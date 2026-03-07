from aiogram.fsm.state import State, StatesGroup


class RegistrationStates(StatesGroup):
    waiting_contact = State()



class AdminExtendStates(StatesGroup):
    waiting_months_or_date = State()
    waiting_custom_date = State()


class AdminBlackoutStates(StatesGroup):
    waiting_start = State()
    waiting_end = State()