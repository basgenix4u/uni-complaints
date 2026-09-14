"""
Response Model
==============
Defines the Response model for complaint responses/comments.
"""

from datetime import datetime
from app.extensions import db


class Response(db.Model):
    """
    Response model representing responses/comments on complaints.
    
    Attributes:
        id: Primary key
        complaint_id: Foreign key to the complaint
        user_id: Foreign key to the user who responded
        message: Response message content
        is_internal: Whether this is an internal note (admin only)
        attachments: JSON field for file attachments
        created_at: Response timestamp
    """
    
    __tablename__ = 'responses'
    
    # Primary Key
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    
    # Foreign Keys
    complaint_id = db.Column(
        db.Integer,
        db.ForeignKey('complaints.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    
    # Response Content
    message = db.Column(db.Text, nullable=False)
    
    # Response Type
    is_internal = db.Column(db.Boolean, default=False, nullable=False)
    
    # Attachments
    attachments = db.Column(db.JSON, default=list)
    
    # Timestamp
    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True
    )
    
    def __init__(self, **kwargs):
        """Initialize response with validated data."""
        super(Response, self).__init__(**kwargs)
        
        # Initialize attachments as empty list if None
        if self.attachments is None:
            self.attachments = []
    
    def to_dict(self, include_author=True):
        """
        Convert response object to dictionary.
        
        Args:
            include_author: Whether to include author information
            
        Returns:
            dict: Response data as dictionary
        """
        data = {
            'id': self.id,
            'complaint_id': self.complaint_id,
            'user_id': self.user_id,
            'message': self.message,
            'is_internal': self.is_internal,
            'attachments': self.attachments or [],
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
        
        # Include author information
        if include_author and self.author:
            data['author'] = {
                'id': self.author.id,
                'full_name': self.author.full_name,
                'role': self.author.role,
                'email': self.author.email
            }
        
        return data
    
    def __repr__(self):
        """String representation of Response."""
        return f'<Response {self.id} on Complaint {self.complaint_id}>'