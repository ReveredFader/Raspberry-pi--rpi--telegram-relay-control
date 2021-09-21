# -*- coding: utf-8 -*-
import logging
import json
import config # API, Users
from sm_h import RPI
import RPi.GPIO as GPIO
# cleanup
import signal
import sys
from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.dispatcher.filters import Command
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage


ALLOWED_PINS = list(range(2, 28))

# log level
logging.basicConfig(level=logging.INFO)

# bot init
bot = Bot(token=config.API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())


# pin init
def init_pin():
    with open("data.json", "r") as read:
        data = json.load(read)
    pins = list(data.values())
    RP = RPI(pins)
    GPIO.setwarnings(False)
    return RP
    

RP = init_pin()


# pin reinit
def reinit_pin():
    with open("data.json", "r") as read:
        data = json.load(read)
    pins = list(data.values())
    RP.re_init_pins(pins)


@dp.message_handler(commands=['help'])
async def process_help_command(message: types.Message):
    await message.reply("Привет! Я бот, разработанный для управления умным домом. Меня могут использовать только те, чьи id добавлены в мою конфигурацию.")


@dp.message_handler(commands=['start'])
async def process_start_command(message: types.Message):
    if message["from"]["id"] in config.USERS:
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(text="Управление розетками", callback_data="rosettes"))
        keyboard.add(types.InlineKeyboardButton(text="Редакция розеток", callback_data="redact_rosette"))
        await message.answer("Привет!\nВыбери что мы будем делать!", reply_markup=keyboard)
    else:
        await message.answer("Я тебя не знаю! Но на всякий случай, твой id " + call["from"]["id"])


@dp.callback_query_handler(text="main")
async def process_start(call: types.CallbackQuery):
    if call["from"]["id"] in config.USERS:
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(text="Управление розетками", callback_data="rosettes"))
        keyboard.add(types.InlineKeyboardButton(text="Редакция розеток", callback_data="redact_rosette"))
        await call.message.edit_text("Привет!\nВыбери что мы будем делать!", reply_markup=keyboard)
    else:
        await call.message.edit_text("Я тебя не знаю! Но на всякий случай, твой id " + call["from"]["id"])


@dp.callback_query_handler(text="rosettes")
async def send_rosettes(call: types.CallbackQuery):
    keyboard = types.InlineKeyboardMarkup()
    with open("data.json", "r") as read:
        data = json.load(read)
    if len(data) > 0:
        for i in data:
            keyboard.add(types.InlineKeyboardButton(text=i, callback_data=i))
    keyboard.add(types.InlineKeyboardButton(text="Главное меню", callback_data="main"))
    await call.message.edit_text("Выберите розетку", reply_markup=keyboard)


@dp.callback_query_handler(text="redact_rosette")
async def redact_rosette(call: types.CallbackQuery):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text="Добавить розетку", callback_data="add_rosette"))
    keyboard.add(types.InlineKeyboardButton(text="Удалить розетку", callback_data="del_rosette"))
    keyboard.add(types.InlineKeyboardButton(text="Вернуть состояние пинов в исходное", callback_data="cleanup"))
    keyboard.add(types.InlineKeyboardButton(text="⬅ Назад в меню", callback_data="main"))
    await call.message.edit_text("Редацкия розеток\nВыберите, что хотите сделать", reply_markup=keyboard)

# Cleanup
@dp.callback_query_handler(text="cleanup")
async def cleanuper(call: types.CallbackQuery):
    GPIO.cleanup()
    await call.answer(text="Готово! Пины сброшены в изночальное состояние", show_alert=True)


# Delete rosette
class DelRosetter(StatesGroup):
    Q1 = State() # Имя розетки

@dp.callback_query_handler(text="del_rosette")
async def enter_test(call: types.CallbackQuery):
    with open("data.json", "r", encoding='utf-8') as read:
        data = json.load(read)
    string = ""
    for i in data:
        string = string + (i + "\n")
    await call.message.answer("Введите название розетки из списка\n" + string)
    await DelRosetter.Q1.set()


@dp.message_handler(state=DelRosetter.Q1)
async def answer_del_q1(message: types.Message, state: FSMContext):
    answer = message.text
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text="Управление розетками", callback_data="rosettes"))
    keyboard.add(types.InlineKeyboardButton(text="Редакция розеток", callback_data="redact_rosette"))

    with open("data.json", "r", encoding='utf-8') as read:
        data = json.load(read)

    if answer in data:
        del data[answer]
        # Сохраним результат
        with open('data.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4, sort_keys=True)
        await message.answer("Розетка удалена!", reply_markup=keyboard)
        await state.finish()
        reinit_pin()
    else:
        await message.answer("Неправильно введено имя розетки!", reply_markup=keyboard)
        await state.finish()


# Add rosette
class AddRosetter(StatesGroup):
    Q1 = State() # Имя розетки
    Q2 = State() # Номер управляющего пина


@dp.callback_query_handler(text="add_rosette")
async def enter_test(call: types.CallbackQuery):
    await call.message.answer("Введите название розетки")
    await AddRosetter.Q1.set()


@dp.message_handler(state=AddRosetter.Q1)
async def answer_q1(message: types.Message, state: FSMContext):
    answer = message.text
    await state.update_data(answer1=answer)
    await message.answer("Введите пин управления")
    await AddRosetter.next()

@dp.message_handler(state=AddRosetter.Q2)
async def answer_q2(message: types.Message, state: FSMContext):
    # Достаем переменные
    data = await state.get_data()
    ans1 = data.get("answer1")
    ans2 = message.text

    # Сразу создадим кнопки
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text="Управление розетками", callback_data="rosettes"))
    keyboard.add(types.InlineKeyboardButton(text="Редакция розеток", callback_data="redact_rosette"))

    # Пытаемся сделать из ответа число, если не получается выводим ошибку
    try:
        ans2 = int(ans2)
    except:
        await message.answer("Неправильно введен пин!", reply_markup=keyboard)
        await state.finish()

    with open("data.json", "r") as read:
        data = json.load(read)

    # Проверяем есть ли уже розетка с таким пином или названием
    if ans1 in data or ans2 in list(data.values()):
        await message.answer("Розетка с таким пином или названием уже существует!", reply_markup=keyboard)

    # Если ответ не стал числом, выводим ошибку
    # elif not isinstance(ans2, int):
    #     await message.answer("Неправильно введен пин!", reply_markup=keyboard)

    # Выводим ошибку если номера пина нет в списке допустимых значений
    elif not ans2 in ALLOWED_PINS:
        await message.answer("Вы не можете использовать данный пин", reply_markup=keyboard)\
    
    else:
        # Если все получилось то добавим эту розетку
        data[ans1] = int(ans2)

        # Сохраняем в json
        with open('data.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4, sort_keys=True)
        
        reinit_pin()
        await message.answer("Розетка добавлена!", reply_markup=keyboard)
    await state.finish()


@dp.callback_query_handler()
async def add_rosette(call: types.CallbackQuery):
    with open("data.json", "r") as read:
        data = json.load(read)
    if call["data"] in data:
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(text="Включить", callback_data="on_" + call["data"]))
        keyboard.add(types.InlineKeyboardButton(text="Выключить", callback_data="off_" + call["data"]))
        keyboard.add(types.InlineKeyboardButton(text="Управление розетками", callback_data="rosettes"))
        await call.message.edit_text("Розетка " + call["data"], reply_markup=keyboard)
    elif call["data"][:3] == "on_":
        if RP.pin_on(data[call["data"][3:]]):
            print("Pin enabled")
            await call.answer(text="Розетка включена", show_alert=True)
    elif call["data"][:4] == "off_":
        if RP.pin_off(data[call["data"][4:]]):
            print("Pin disabled")
            await call.answer(text="Розетка выключена", show_alert=True)


# Cleanup
def signal_handler(signal, frame):
    print('You pressed Ctrl+C - or killed me with -2')
    GPIO.cleanup()
    sys.exit(0)
signal.signal(signal.SIGINT, signal_handler)


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)