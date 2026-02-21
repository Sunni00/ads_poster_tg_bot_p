from aiogram.fsm.state import State, StatesGroup


class RegistrationStates(StatesGroup):
    waiting_contact = State()


class AdStates(StatesGroup):
    collecting = State()   # user freely sends photos/text/audio
    confirm = State()      # user sees preview and confirms


class AdminExtendStates(StatesGroup):
    waiting_months_or_date = State()
    waiting_custom_date = State()


class AdminBlackoutStates(StatesGroup):
    waiting_start = State()
    waiting_end = State()