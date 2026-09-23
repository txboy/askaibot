from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import get_current_user
from ..common import get_setting
from ..database import get_db

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("", response_model=list[schemas.ConversationOut])
def list_conversations(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(models.Conversation)
        .filter(models.Conversation.user_id == user.id)
        .order_by(models.Conversation.updated_at.desc())
        .all()
    )


@router.post("", response_model=schemas.ConversationOut)
def create_conversation(
    payload: schemas.ConversationCreate,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    setting = get_setting(db)
    conversation = models.Conversation(
        user_id=user.id,
        title=payload.title or "新对话",
        model=payload.model or setting.default_model,
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


@router.put("/{conversation_id}", response_model=schemas.ConversationOut)
def rename_conversation(
    conversation_id: int,
    payload: schemas.ConversationUpdate,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversation = _get_owned(db, conversation_id, user)
    conversation.title = payload.title
    db.commit()
    db.refresh(conversation)
    return conversation


@router.delete("/{conversation_id}")
def delete_conversation(
    conversation_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversation = _get_owned(db, conversation_id, user)
    db.query(models.Message).filter(
        models.Message.conversation_id == conversation.id
    ).delete()
    db.delete(conversation)
    db.commit()
    return {"ok": True}


@router.get("/{conversation_id}/messages", response_model=list[schemas.MessageOut])
def list_messages(
    conversation_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversation = _get_owned(db, conversation_id, user)
    msgs = (
        db.query(models.Message)
        .filter(models.Message.conversation_id == conversation.id)
        .order_by(models.Message.id.asc())
        .all()
    )
    result = []
    for m in msgs:
        atts = (
            db.query(models.Attachment)
            .filter(models.Attachment.message_id == m.id)
            .all()
        )
        result.append(
            schemas.MessageOut(
                id=m.id,
                role=m.role,
                content=m.content,
                created_at=m.created_at,
                attachments=[a for a in atts],
            )
        )
    return result


def _get_owned(
    db: Session, conversation_id: int, user: models.User
) -> models.Conversation:
    conversation = db.get(models.Conversation, conversation_id)
    if not conversation or conversation.user_id != user.id:
        raise HTTPException(status_code=404, detail="会话不存在")
    return conversation
