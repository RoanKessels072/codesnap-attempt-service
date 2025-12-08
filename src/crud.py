from sqlalchemy.orm import Session
from sqlalchemy import func
from src.models import Attempt
from datetime import datetime, timezone


def create_attempt(
    db: Session, 
    user_id: int, 
    exercise_id: int, 
    code: str,
    stars: int = 0,
    score: int = 0
) -> Attempt:    
    if not code or not code.strip():
        raise ValueError("Code cannot be empty")
    
    attempt = Attempt(
        user_id=user_id,
        exercise_id=exercise_id,
        code_submitted=code,
        stars=stars,
        score=score,
        attempted_at=datetime.now(timezone.utc)
    )
    
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    
    return attempt


def get_attempt_by_id(db: Session, attempt_id: int):
    return db.query(Attempt).filter(Attempt.id == attempt_id).first()


def get_user_attempts(db: Session, user_id: int):
    attempts = db.query(Attempt).filter(
        Attempt.user_id == user_id
    ).order_by(
        Attempt.attempted_at.desc()
    ).all()
    
    result = []
    for attempt in attempts:
        result.append({
            'id': attempt.id,
            'exercise_id': attempt.exercise_id,
            'score': attempt.score,
            'stars': attempt.stars,
            'attempted_at': attempt.attempted_at.isoformat()
        })
    
    return result


def get_exercise_attempts(db: Session, exercise_id: int, limit: int = None):
    query = db.query(Attempt).filter(
        Attempt.exercise_id == exercise_id
    ).order_by(
        Attempt.attempted_at.desc()
    )
    
    if limit:
        query = query.limit(limit)
    
    return query.all()


def get_best_attempt_for_exercise(db: Session, user_id: int, exercise_id: int):
    attempt = db.query(Attempt).filter(
        Attempt.user_id == user_id,
        Attempt.exercise_id == exercise_id
    ).order_by(
        Attempt.stars.desc(),
        Attempt.score.desc(),
        Attempt.attempted_at.desc()
    ).first()
    
    if attempt:
        return {
            "id": attempt.id,
            "exercise_id": attempt.exercise_id,
            "stars": attempt.stars,
            "score": attempt.score,
            "attempted_at": attempt.attempted_at.isoformat(),
            "code_submitted": attempt.code_submitted
        }
    return None


def get_user_best_attempts(db: Session, user_id: int):
    subquery = db.query(
        Attempt.exercise_id,
        func.max(
            Attempt.stars * 100 + Attempt.score * 10 + 
            func.extract('epoch', Attempt.attempted_at) / 1000000000
        ).label('best_score')
    ).filter(
        Attempt.user_id == user_id
    ).group_by(
        Attempt.exercise_id
    ).subquery()
    
    attempts = db.query(Attempt).join(
        subquery,
        (Attempt.exercise_id == subquery.c.exercise_id)
    ).filter(
        Attempt.user_id == user_id
    ).order_by(
        Attempt.stars.desc(),
        Attempt.score.desc(),
        Attempt.attempted_at.desc()
    ).all()
    
    best_attempts = {}
    for attempt in attempts:
        if attempt.exercise_id not in best_attempts:
            best_attempts[attempt.exercise_id] = {
                "exercise_id": attempt.exercise_id,
                "stars": attempt.stars,
                "score": attempt.score,
                "attempted_at": attempt.attempted_at.isoformat()
            }
    
    return best_attempts
