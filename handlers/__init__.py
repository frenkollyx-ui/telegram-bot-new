from .profile import router as profile_router
from .bank import router as bank_router
from .mining import router as mining_router
from .casino import router as casino_router
from .cases import router as cases_router
from .clan import router as clan_router
from .marriage import router as marriage_router
from .business import router as business_router
from .admin import router as admin_router
from .misc import router as misc_router


def register_all_handlers(dp):
    dp.include_router(profile_router)
    dp.include_router(bank_router)
    dp.include_router(mining_router)
    dp.include_router(casino_router)
    dp.include_router(cases_router)
    dp.include_router(clan_router)
    dp.include_router(marriage_router)
    dp.include_router(business_router)
    dp.include_router(admin_router)
    dp.include_router(misc_router)
