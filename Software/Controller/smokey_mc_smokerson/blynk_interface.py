import blynklib
import random
import time
import blynktimer
from datetime import datetime
from datetime import timedelta  
import globals

#Set Globals
config = globals.config
cooking_dict = globals.cooking_dict

#Connect to Blynk server
if (config['blynk']['server'] == ''):
    blynk = blynklib.Blynk(config['blynk']['auth'])
    
else:
    blynk = blynklib.Blynk(config['blynk']['auth'], server=config['blynk']['server'], port=config['blynk']['server_port'])

#Initialize Blynk Timer
timer = blynktimer.Timer()

#Set base strings
READ_PRINT_MSG = "[READ_VIRTUAL_PIN_EVENT] Pin: V{}"
WRITE_EVENT_PRINT_MSG = "[WRITE_VIRTUAL_PIN_EVENT] Pin: V{} Value: '{}'"
recipe_info_string = "Recipe: {}\n\nMeat Type: {}\n\nSmoker Temperature: {}C\n\nTarget Meat Temperature: {}C\n\nCooking Time: {}\n\nInfo:\n{}"

#Set base variable
cooking_start = None
cooking_end = None
selected_profile = 1
init_loop = True
manual_timer_hours = 0
manual_timer_minutes = 0
timer_notification_sent = False

#Set Blynk Vpins
current_barrel_temp_vpin = config['blynk']['vpins']['current_barrel_temp']['pin']
current_meat_temp_vpin = config['blynk']['vpins']['current_meat_temp']['pin']
target_barrel_temp_vpin = config['blynk']['vpins']['target_barrel_temp']['pin']
target_meat_temp_vpin = config['blynk']['vpins']['target_meat_temp']['pin']
recipe_selector_vpin = config['blynk']['vpins']['recipe_selector']['pin']
status_text_vpin = config['blynk']['vpins']['status_text']['pin']
fan_speed_vpin = config['blynk']['vpins']['fan_speed']['pin']
recipe_description_vpin = config['blynk']['vpins']['recipe_description']['pin']
cook_time_remaining_vpin = config['blynk']['vpins']['cook_time_remaining']['pin']
manual_timer_hours_vpin = config['blynk']['vpins']['manual_timer_hours']['pin']
manual_timer_minutes_vpin = config['blynk']['vpins']['manual_timer_minutes']['pin']
confirm_recipe_vpin = config['blynk']['vpins']['confirm_recipe']['pin']
set_manual_timer_vpin = config['blynk']['vpins']['set_manual_timer']['pin']
mode_selector_vpin = config['blynk']['vpins']['mode_selector']['pin']
current_pid_kp_vpin = config['blynk']['vpins']['current_pid_kp']['pin']
current_pid_ki_vpin = config['blynk']['vpins']['current_pid_ki']['pin']
current_pid_kd_vpin = config['blynk']['vpins']['current_pid_kd']['pin']
current_pid_profile_vpin = config['blynk']['vpins']['current_pid_profile']['pin']
current_temp_gap_vpin = config['blynk']['vpins']['current_temp_gap']['pin']
manual_pid_kp_vpin = config['blynk']['vpins']['manual_pid_kp']['pin']
manual_pid_ki_vpin = config['blynk']['vpins']['manual_pid_ki']['pin']
manual_pid_kd_vpin = config['blynk']['vpins']['manual_pid_kd']['pin']
pid_profile_override_vpin = config['blynk']['vpins']['pid_profile_override']['pin']

def strfdelta(tdelta, fmt):
    d = {"days": tdelta.days}
    d["hours"], rem = divmod(tdelta.seconds, 3600)
    d["minutes"], d["seconds"] = divmod(rem, 60)
    d["hours"] = str(d["hours"]).rjust(2, '0')
    d["minutes"] = str(d["minutes"]).rjust(2, '0')
    d["seconds"] = str(d["seconds"]).rjust(2, '0')
    return fmt.format(**d)
          
@timer.register(interval=5, run_once=False)
def update_ui():
    global timer_notification_sent

    blynk.virtual_write(current_barrel_temp_vpin, int(globals.current_barrel_temp))
    blynk.virtual_write(current_meat_temp_vpin, int(globals.current_meat_temp))
    blynk.virtual_write(fan_speed_vpin, globals.fan_speed)
    blynk.virtual_write(current_pid_kp_vpin, globals.current_pid_kp)
    blynk.virtual_write(current_pid_ki_vpin, globals.current_pid_ki)
    blynk.virtual_write(current_pid_kd_vpin, globals.current_pid_kd)
    blynk.virtual_write(current_pid_profile_vpin, globals.current_pid_profile)
    blynk.virtual_write(current_temp_gap_vpin, int(globals.current_temp_gap))

    if (cooking_end):
        time_delta = cooking_end - datetime.now()
        if (time_delta.days >= 0):
            message = strfdelta(time_delta, "{hours}:{minutes}:{seconds}")
        else:
            message = "Ready"
            if (timer_notification_sent == False):
                blynk.notify("Food is ready")
                timer_notification_sent = True
        
        blynk.virtual_write(cook_time_remaining_vpin, message)

@blynk.handle_event('write V{}'.format(target_barrel_temp_vpin))
def write_target_barrel_temp_handler(pin, value):
    print(WRITE_EVENT_PRINT_MSG.format(pin, value))
    globals.target_barrel_temp = int(value[0])

@blynk.handle_event('write V{}'.format(target_meat_temp_vpin))
def write_target_meat_temp_handler(pin, value):
    print(WRITE_EVENT_PRINT_MSG.format(pin, value))
    globals.target_meat_temp = int(value[0])

@blynk.handle_event('write V{}'.format(recipe_selector_vpin))
def write_recipe_selector_handler(pin, value):
    global selected_profile
    index = value[0]
    selected_profile = index
    print(WRITE_EVENT_PRINT_MSG.format(pin, value))

    blynk.virtual_write(recipe_description_vpin, 'clr')
    blynk.virtual_write(recipe_description_vpin, recipe_info_string.format(cooking_dict[index]['name'], cooking_dict[index]['meat_type'], cooking_dict[index]['barrel_temp'], cooking_dict[index]['meat_temp'], time.strftime('%H:%M:%S', time.gmtime(cooking_dict[index]['cooking_time'])), cooking_dict[index]['description']))

@blynk.handle_event('write V{}'.format(confirm_recipe_vpin))
def write_confirm_recipe_handler(pin, value):
    global cooking_end
    global cooking_start
    global timer_notification_sent

    print(WRITE_EVENT_PRINT_MSG.format(pin, value))

    if(value[0] == "1"):
        index = selected_profile    
        blynk.virtual_write(target_barrel_temp_vpin, cooking_dict[index]['barrel_temp'])
        globals.target_barrel_temp = cooking_dict[index]['barrel_temp']
        blynk.virtual_write(target_meat_temp_vpin, cooking_dict[index]['meat_temp'])
        globals.target_meat_temp = cooking_dict[index]['meat_temp']
        blynk.virtual_write(status_text_vpin, 'Cooking: {} - {}'.format(cooking_dict[index]['meat_type'], cooking_dict[index]['name']))
        blynk.virtual_write(recipe_description_vpin, '\n\n[+] Auto Mode Set')
        blynk.virtual_write(mode_selector_vpin, '2')

        cooking_end = datetime.now() + timedelta(seconds=cooking_dict[index]['cooking_time'])
        cooking_start = datetime.now()
        timer_notification_sent = False
    
@blynk.handle_event('write V{}'.format(manual_timer_hours_vpin))
def write_manual_timer_hours_handler(pin, value):
    global manual_timer_hours
    manual_timer_hours = int(value[0])
    print(WRITE_EVENT_PRINT_MSG.format(pin, value))

@blynk.handle_event('write V{}'.format(manual_timer_minutes_vpin))
def write_manual_timer_minutes_handler(pin, value):
    global manual_timer_minutes
    manual_timer_minutes = int(value[0])
    print(WRITE_EVENT_PRINT_MSG.format(pin, value))

@blynk.handle_event('write V{}'.format(set_manual_timer_vpin))
def write_set_manual_timer_handler(pin, value):
    global cooking_end
    global cooking_start
    global timer_notification_sent

    print(WRITE_EVENT_PRINT_MSG.format(pin, value))
    blynk.virtual_write(mode_selector_vpin, '1')
    blynk.virtual_write(status_text_vpin, 'Manual Mode')

    cooking_end = datetime.now() + timedelta(hours=manual_timer_hours, minutes=manual_timer_minutes)
    cooking_start = datetime.now()
    timer_notification_sent = False

@blynk.handle_event('write V{}'.format(manual_pid_kp_vpin))
def write_manual_pid_kp_val_handler(pin, value):
    print(WRITE_EVENT_PRINT_MSG.format(pin, value))
    globals.manual_pid_kp = float(value[0])

@blynk.handle_event('write V{}'.format(manual_pid_ki_vpin))
def write_manual_pid_ki_val_handler(pin, value):
    print(WRITE_EVENT_PRINT_MSG.format(pin, value))
    globals.manual_pid_ki = float(value[0])

@blynk.handle_event('write V{}'.format(manual_pid_kd_vpin))
def write_manual_pid_KD_val_handler(pin, value):
    print(WRITE_EVENT_PRINT_MSG.format(pin, value))
    globals.manual_pid_kd = float(value[0])

@blynk.handle_event('write V{}'.format(pid_profile_override_vpin))
def write_pid_override_handler(pin, value):
    print(WRITE_EVENT_PRINT_MSG.format(pin, value))
    if (int(value[0]) == 1):
        globals.pid_profile_override = True

    elif (int(value[0]) == 0):
        globals.pid_profile_override = False



@blynk.handle_event("connect")
def connect_handler():
    menu_list = []
    for menu_item in cooking_dict:
        menu_list.append(cooking_dict[menu_item]['name'])
    menu_string = '"' + '","'.join(map(str, menu_list)) + '"'
    blynk.set_property(recipe_selector_vpin, "labels", *menu_list)
    blynk.notify("Received new menu")


def run_blynk():
    global init_loop
    while True:
        blynk.run()
        if (init_loop == True):
            blynk.virtual_write(status_text_vpin, 'Warming up')
            blynk.virtual_write(cook_time_remaining_vpin, '-')
            blynk.virtual_write(mode_selector_vpin, '1')
        
            blynk.virtual_write(manual_timer_hours_vpin, '0')
            blynk.virtual_write(manual_timer_minutes_vpin, '0')

            blynk.virtual_write(target_barrel_temp_vpin, globals.target_barrel_temp)
            blynk.virtual_write(target_meat_temp_vpin, globals.target_meat_temp)

            blynk.virtual_write(manual_pid_kp_vpin, globals.manual_pid_kp)
            blynk.virtual_write(manual_pid_ki_vpin, globals.manual_pid_ki)
            blynk.virtual_write(manual_pid_kd_vpin, globals.manual_pid_kd)
            blynk.virtual_write(pid_profile_override_vpin, 0)

            init_loop = False

        timer.run()