from ntpath import join
from pystray import MenuItem as item
import pystray
from PIL import Image
from datetime import datetime
import schedule
import time
from instabot import Bot
import os
from pathlib import Path
import shutil
import configparser
import tkinter as tk
import threading
import sys
import getpass

######################BEGIN VISUAL REGION######################

root = tk.Tk()
root.iconbitmap(os.path.dirname(os.path.realpath(__file__)) + "\\icon.ico")
root.title("InstaFoto")
root.resizable(0,0)

######################BEGIN RUN ON WINDOWS STARTUP#############
USER_NAME = getpass.getuser()

def add_to_startup(file_path=""):
    bat_path = r'C:\Users\%s\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup' % USER_NAME
    full_file_name = bat_path + '\\' + "open.bat"

    if on_startup.get() == 1:
        if file_path == "":
            file_path = os.path.dirname(os.path.realpath(__file__))

        with open(full_file_name, "w+") as bat_file:
            bat_file.write(r'start "" /d "%s" "InstaFoto.exe"' % file_path)
    else:
        if os.path.exists(full_file_name):
            os.remove(full_file_name)

def set_run_on_startup():
    config.set("Config", "RunOnWindowsStartup", str(on_startup.get()))
    cfgfile = open('configuracion.txt','w')
    config.write(cfgfile, space_around_delimiters=False)  # use flag in case case you need to avoid white space.
    cfgfile.close()

    add_to_startup()

on_startup = tk.IntVar()

tk.Checkbutton(root, text="Ejecutar al inicio de Windows", variable=on_startup, onvalue=1, 
            offvalue=0, command=set_run_on_startup).pack()

######################END RUN ON WINDOWS STARTUP###############

scrollbar = tk.Scrollbar(root)
scrollbar.pack( side = tk.RIGHT, fill = tk.Y )

display_label = tk.Listbox(root, width=55, height=25, yscrollcommand = scrollbar.set )
display_label.insert(tk.END, "Iniciando el programa...")

display_label.pack( side = tk.LEFT, fill = tk.BOTH )
scrollbar.config( command = display_label.yview )

in_tray= False
label_queue= []

def update_label(new_status):
    global in_tray, label_queue
    if in_tray:
       label_queue.append(new_status)
    else:
        display_label.insert(tk.END, new_status)



def quit_window(icon, item):
    icon.visible=False
    update_label("Cerrando")
    icon.stop()
    bot.logout()
    root.destroy()
    sys.exit()
    
def show_window(icon, item):
   global in_tray, label_queue
   in_tray= False
   icon.stop()
   root.after(0,root.deiconify())
   for i in label_queue:
       display_label.insert(tk.END, i)
   label_queue.clear()    

def hide_window():
    global in_tray
    in_tray= True
    root.withdraw()
    icon_image=Image.open("icon.ico")
    menu=pystray.Menu(item('Mostrar', show_window), item('Cerrar', quit_window))
    icon=pystray.Icon("name", icon_image, "InstaFoto", menu)
    icon.run()
    

####################END VISUAL REGION##########################

def clean_dir():
    update_label("Inicializando conexión...")
    
    dir = "config"

    if os.path.exists(dir):
        try:
            shutil.rmtree(dir)
        except OSError as e:
             print("Error: %s - %s." % (e.filename, e.strerror))

clean_dir()

bot = Bot()
time.sleep(3)

path=Path().absolute()
PARENT_DIRECTORY = path
IMAGES_DIRECTORY= os.path.join(PARENT_DIRECTORY,'imagenes')

b_imgs = False
config = configparser.ConfigParser()
config.read_file(open('configuracion.txt'))
username= config.get('Instagram', 'usuario')
password = config.get('Instagram', 'contra')
_username= config.get('Instagram', 'usuario')
_password= config.get('Instagram', 'contra')
_caption= config.get('Posteo','caption')
_run_on_startup = config.get('Config', 'RunOnWindowsStartup')
on_startup.set(_run_on_startup)


def clean_img(_imgname):
    remove_me =os.path.join(IMAGES_DIRECTORY, _imgname + '.REMOVE_ME')
    
    if os.path.exists(remove_me):
        new_name_without_removeme =os.path.join(IMAGES_DIRECTORY,_imgname)
        os.rename(remove_me,new_name_without_removeme)

def upload_img(_imgname = 'EMPTY'):
    if(_imgname == 'EMPTY'):
        update_label("ERROR: No se encontro una imagen")
        return
    else:
        clean_img(_imgname)
        update_label("Subiendo "+_imgname+"! - " + datetime.now().strftime("%d/%m/%Y, %H:%M"))
        bot.upload_photo(os.path.join(IMAGES_DIRECTORY, _imgname),
                        caption = _caption)
        
        if bot.api.last_response.status_code != 200:         
            update_label("ERROR: " + bot.api.last_response)
        else:
            update_label("Subido exitosamente!")
            update_label("Todo listo, esperando...")

def login():
    update_label("Conectando....")

    bot.login(username = _username,
                password = _password,
                is_threaded=True)
    

def setup_schedules():
    global b_imgs

    update_label("Buscando horarios.....")

    schedule_when = config.items('Horarios')

    for (each_key, each_val) in schedule_when:
        date = each_val.split("-")[0].lower()
        time = each_val.split("-")[1]
        
        try:
            img_name = each_val.split("-")[2]
        except IndexError as e:
            update_label("ERROR: No se encontro imagen para el dia " + date + " a las " + time)
            continue

        update_label("Dia detectado! " + date + " a las " + time + " (" + img_name + ")")

        b_imgs = True

        if(date == "lu"):
            schedule.every().monday.at(time).do(upload_img, img_name)
        if(date == "ma"):
            schedule.every().tuesday.at(time).do(upload_img,img_name)
        if(date == "mi"):
            schedule.every().wednesday.at(time).do(upload_img, img_name)
        if(date == "ju"):
            schedule.every().thursday.at(time).do(upload_img, img_name)
        if(date == "vi"):
            schedule.every().friday.at(time).do(upload_img, img_name)
        if(date == "sa"):
            schedule.every().saturday.at(time).do(upload_img, img_name)
        if(date == "do"):
            schedule.every().sunday.at(time).do(upload_img, img_name)


def run_continuously(interval=1):
       
        cease_continuous_run = threading.Event()

        class ScheduleThread(threading.Thread):
            @classmethod
            def run(cls):
                while not cease_continuous_run.is_set():
                    schedule.run_pending()
                    time.sleep(interval)

        continuous_thread = ScheduleThread()
        continuous_thread.start()
        return cease_continuous_run

def start_scheduling():
    global b_imgs

    login()
    setup_schedules()

    time.sleep(2)

    if(b_imgs):
        update_label("Todo listo, esperando...")
    else:
        update_label("ERROR: No se detectaron imagenes para subir")
    
    run_continuously()


add_to_startup()

t1 = threading.Thread(target=start_scheduling)
t1.setDaemon(True)
t1.start()
root.protocol("WM_DELETE_WINDOW", hide_window)
root.mainloop()
