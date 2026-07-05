"""Root model aggregator.

Importing this module imports every feature module's models, which registers
all SQLModel tables on ``SQLModel.metadata`` (used by ``create_db_and_tables``).
It also re-exports the model/schema classes for convenience.
"""
from app.modules.user.models import *      # noqa: F401,F403
from app.modules.consultant.models import *  # noqa: F401,F403
from app.modules.appointment.models import *  # noqa: F401,F403
from app.modules.consultation.models import *  # noqa: F401,F403
from app.modules.meal.models import *      # noqa: F401,F403
from app.modules.notification.models import *  # noqa: F401,F403
from app.modules.meal_planner_agent.plan_setup_models import *  # noqa: F401,F403
from app.modules.plan.models import *  # noqa: F401,F403
