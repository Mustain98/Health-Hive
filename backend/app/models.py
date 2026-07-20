"""Root model aggregator.

Importing this module imports every model module, which registers all SQLModel tables
on ``SQLModel.metadata`` (used by ``create_db_and_tables``).
"""
from app.modules.user.models import *              # noqa: F401,F403
from app.modules.milestone.models import *         # noqa: F401,F403
from app.modules.daily_goal.models import *        # noqa: F401,F403
from app.modules.nutrition_target.models import *  # noqa: F401,F403
from app.modules.daily_log.models import *         # noqa: F401,F403
from app.modules.meal_plan_setting.models import * # noqa: F401,F403
from app.modules.plan.models import *              # noqa: F401,F403
from app.modules.consultant.models import *        # noqa: F401,F403
from app.modules.appointment.models import *       # noqa: F401,F403
from app.modules.consultation.models import *      # noqa: F401,F403
from app.modules.meal.models import *              # noqa: F401,F403
from app.modules.notification.models import *      # noqa: F401,F403
from app.agents.setup_chat.models import *         # noqa: F401,F403
