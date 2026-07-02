"""Root schema aggregator — re-exports every feature module's schemas."""
from app.modules.user.schemas import *        # noqa: F401,F403
from app.modules.consultant.schemas import *  # noqa: F401,F403
from app.modules.appointment.schemas import *  # noqa: F401,F403
from app.modules.consultation.schemas import *  # noqa: F401,F403
from app.modules.meal.schemas import *        # noqa: F401,F403
