# Import all the models, so that Base has them before being
# imported by Migrations or Alembic
from app.db.session import Base  # noqa
from app.models.user import User  # noqa
from app.models.role import Role  # noqa
from app.models.complaint import Complaint  # noqa
from app.models.comment import Comment  # noqa
from app.models.hostel import Hostel  # noqa
from app.models.room import Room  # noqa
from app.models.notice import Notice  # noqa
from app.models.emergency import Emergency  # noqa
from app.models.emergency_hotline import EmergencyHotline  # noqa

