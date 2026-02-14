from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class TicketLink(Base):
    __tablename__ = "ticket_links"
    
    id = Column(Integer, primary_key=True, index=True)
    source_ticket_id = Column(Integer, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False)
    target_ticket_id = Column(Integer, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False)
    link_type = Column(String(50), default="related")  # related, blocks, blocked_by, duplicates, parent, child
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    source_ticket = relationship("Ticket", foreign_keys=[source_ticket_id])
    target_ticket = relationship("Ticket", foreign_keys=[target_ticket_id])
    creator = relationship("User", foreign_keys=[created_by])
