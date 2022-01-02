import os
from sys import executable, argv, settrace
from threading import Thread
import trace
import shutil
import tempfile
import json
from abc import ABC, abstractmethod
from urllib import request
import zipfile
from time import time, sleep
import __main__ as main
from tkinter import Tk, PhotoImage
from tkinter.ttk import Frame, Label, Button, Progressbar


class CallBacks():
    def __init__(self, CallBackGauge, CallBackStatus, CallBackCancel) -> None:
        self.CallBackGauge = CallBackGauge
        self.CallBackStatus = CallBackStatus
        self.CallBackCancel = CallBackCancel
    
    def DoCallBackForward(self, status, gauge):
        if self.CallBackStatus != None:
            self.CallBackStatus(status)
        if self.CallBackGauge != None:
            self.CallBackGauge(gauge)
    
    def DoCancel(self):
        self.DoCallBackForward("Fechando...", 100)
        self.CallBackCancel()

    def DoUpdateStatus(self, status):
        if self.CallBackStatus != None:
            self.CallBackStatus(status)

class DoTheUpdate():
    def __init__(self, AppSelf):
        self.cancel = False
        self.GetNewFiles = AppSelf.GetNewFiles
        self.temp_folder = "Simple_Updater_" + str(time())
        self.AppSelf = AppSelf
    
    def Stage1_download(self, temp_app_folder):
        self.call_backs.DoCallBackForward("Baixando nova versão, aguarde...", 2)
        get_file = self.GetNewFiles(temp_app_folder)
        if get_file != True:
            self.call_backs.DoCallBackForward(f"Ocorreu um erro ao baxiar o arquivo {get_file} - Fechando em 5", 2)
            sleep(5)
            self.call_backs.DoCancel()
            self.CancelUpdate()
        else:
            self.call_backs.DoCallBackForward("Os arquivos necessários foram baixados, Instalando...", 50)

    def Stage2_bkpFiles(self, app_folder, bkp_folder):
        if os.path.isdir(bkp_folder):
            shutil.rmtree(bkp_folder)               
        file_names = os.listdir(app_folder)
        os.mkdir(bkp_folder)
        for f in file_names:
            shutil.move(os.path.join(app_folder, f), os.path.join(bkp_folder,f))
    
    def revert_stage2(self, app_folder, bkp_folder):
        self.call_backs.DoCallBackForward("Revertendo mundaças, aguarde...", 50)
        file_names = os.listdir(bkp_folder)
        for f in file_names:
            shutil.move(os.path.join(bkp_folder, f), os.path.join(app_folder,f))
        self.call_backs.DoCancel()

    def Stage3_moveFiles(self, temp_app_folder, app_folder):
        self.call_backs.DoCallBackForward("Copiando arquivos, aguarde...", 52)
        new_file_name = os.listdir(temp_app_folder)
        exec_file_name = os.path.split(main.__file__)[1]
        dot = exec_file_name.rindex(".")
        try:
            with zipfile.ZipFile(os.path.join(temp_app_folder, new_file_name[0]), 'r') as zip:
                to_remove = False
                for file in zip.namelist():
                    if file[-1] == '/':
                        continue
                    try:
                        file_dot = file.rindex(".")
                    except Exception:
                        continue
                    if (os.path.split(file[:file_dot])[1])  == exec_file_name[:dot]:
                        to_remove = len(os.path.split(file)[0])
                if to_remove:
                    for zip_info in zip.infolist():
                        if zip_info.filename[-1] == '/':
                            continue
                        zip_info.filename = zip_info.filename[to_remove:]
                        zip.extract(zip_info, app_folder)
        except Exception as error:
            self.call_backs.DoCallBackForward("Ocorreu um erro ao extrair os arquivos.... Revertendo as mudanças", 52)
            sleep(3)
            self.call_backs.DoCancel()

    def revert_stage3(self, app_folder, bkp_folder):
        self.call_backs.DoCallBackForward("Ocorreu um erro ao reinicar o aplicativo! Revertendo as mudanças, aguarde...", 52)
        file_names = os.listdir(bkp_folder)
        for f in file_names:
            shutil.move(os.path.join(bkp_folder, f), os.path.join(app_folder,f))
        self.call_backs.DoCancel()

    def Stage4_restartAndCheckUpate(self, app_folder, bkp_folder):
        updated = self.AppSelf.DoWeNeedToUpdate()
        exec_file_copied = False
        exe_main_file = os.path.split(main.__file__)[1]
        exe_main_file_dot = exe_main_file.rindex(".")
        for file in os.listdir(app_folder):
            try:
                file_dot = file.rindex(".")
            except Exception:
                continue
            if file[:file_dot] == exe_main_file[:exe_main_file_dot]:
                exec_file_copied = True
        if exec_file_copied and updated:
            self.AppSelf.restart_program(bkp_folder)
        else:
            self.revert_stage3(app_folder, bkp_folder)

    def DoUpdate(self, CallBackGauge = None, CallBackStatus = None, CallBackCancel = None):
        self.call_backs = CallBacks(CallBackGauge, CallBackStatus, CallBackCancel)
        self.call_backs.DoCallBackForward("Criando pasta para arquivos temporários...", 1)
        temp_app_folder = os.path.join(tempfile.gettempdir(), self.temp_folder)
        if not os.path.isdir(temp_app_folder):os.mkdir(temp_app_folder)
        if not self.cancel:
            self.Stage1_download(temp_app_folder)
            if not self.cancel:
                app_folder = os.getcwd()
                bkp_folder = os.path.join(app_folder, "_BKP")
                self.Stage2_bkpFiles(app_folder, bkp_folder)
                if not self.cancel:
                    self.Stage3_moveFiles(temp_app_folder, app_folder)
                    if not self.cancel:
                        self.Stage4_restartAndCheckUpate(app_folder, bkp_folder)
                    else:
                        self.revert_stage3(app_folder, bkp_folder)
                else:
                    self.revert_stage2(app_folder, bkp_folder)
            else:
                self.call_backs.DoCancel()
        else:
            self.call_backs.DoCancel()

    def CancelUpdate(self):
        self.cancel = True

class SimpleUpdater(ABC):
    ''' Simple Updater main class, recieves a location to a json file and check the app version and compare with a local one. Optionally a relative path can be passed for the local json file. Egg: /includes/ '''

    def __init__(self, file_location: str, json_relative_path: str, app_image: str = None):
        self.file_location = file_location
        self.current_json_file_path = os.path.join(os.getcwd(), json_relative_path)
        self.app_image = app_image

    def LocalJson(self):
        if os.path.isfile(self.current_json_file_path):
            with open(self.current_json_file_path) as f:
                Version_Ctrl = json.load(f)
            return Version_Ctrl
        else: return False
    
    @abstractmethod
    def GetJsonFile(self):
        ''' Gets the json object to check the upstream version, if the file is locally configured (internal netwok) '''
    
    @abstractmethod
    def GetNewFiles(self):
        ''' Gets the updated program files from the correct source '''

    def DoWeNeedToUpdate(self, callback = None):
        ''' Compare the upstream json file with the local file '''

        local_json_file = self.LocalJson()
        self.remote_json = self.GetJsonFile()
        if self.remote_json and local_json_file:
            try:
                if local_json_file["Version"] == self.remote_json["Version"]:
                    if callback:
                        callback(True)
                    else:
                        return True
                else:
                    if callback:
                        callback((local_json_file['Version'], self.remote_json['Version']))
                    else:
                        return (local_json_file['Version'], self.remote_json['Version'])
            except:
                if callback:
                    callback(False)
                else:
                    return False
        else:
            if callback:
                callback(False)
            else:
                return False
    
    def Update(self):
        if argv[-1] == "SelfRestarted":
            try:
                shutil.rmtree(argv[-2])
            except Exception:
                pass
            finally:
                return argv[-1]
        update = self.DoWeNeedToUpdate()
        if update != False and update!= True:
            if update[0] < update[1]:
                try:
                    question_text = self.remote_json["question_text"]
                except:
                    question_text = "O aplicativo tem uma atualização disponível! Você quer atualizar agora?"
                try:
                    question_title = self.remote_json["question_title"]
                except:
                    question_title = "Simple Updater"
                #update_Question = AskToUpdate(question_text, question_title)
                #if update_Question.update:
                    update_obj = DoTheUpdate(self)
                #    UpdateProgress(question_title, update_obj.DoUpdate, update_obj.CancelUpdate, self.app_image)
        return update
    
    def restart_program(self, folder_to_Remove):
        """Restarts the current program.
        Note: this function does not return. Any cleanup action (like
        saving data) must be done before calling this function."""
        python = executable
        os.execl(python, python, * argv, folder_to_Remove, "SelfRestarted")


class SimpleUpdaterLocal(SimpleUpdater):

    def __init__(self, file_location: str, json_relative_path: str, app_image: str = None):
        self.json_relative_path = json_relative_path
        super().__init__(file_location, json_relative_path, app_image)

    def GetJsonFile(self):
        ''' Gets the json object to check the upstream version, if the file is locally configured (internal netwok) '''

        Version_Ctrl = False
        if os.path.isfile(self.file_location):
            with zipfile.ZipFile(self.file_location, 'r') as zip:
                files = zip.namelist()
                for file in files:
                    if file.endswith(os.path.split(self.json_relative_path)[1]):
                        Version_Ctrl = file
                if Version_Ctrl:
                    read_json = zip.read(Version_Ctrl)
                    Version_Ctrl = json.loads(read_json.decode("utf-8"))        
        return Version_Ctrl

    def GetNewFiles(self, dest):
        try:
            shutil.copy(self.file_location, dest)
            return True
        except Exception as error:
            return error

class SimpleUpdaterUrl(SimpleUpdater):
    
    def __init__(self, file_location: str, json_relative_path: str, json_file_location: str, app_image: str = None):
        self.json_file_location = json_file_location
        super().__init__(file_location, json_relative_path, app_image)
        
    
    def GetJsonFile(self):
        ''' Gets the json object to check the upstream version, if the file is locally configured (internal netwok) '''
        try:
            file = request.urlopen(self.json_file_location).read()
            Version_Ctrl = json.loads(file)
            return Version_Ctrl
        except IOError:
            return "Erro retrieving the .json file to check updates!"
    
    def GetNewFiles(self, dest):
        abs_dest_file_name = os.path.join(dest, os.path.split(self.file_location)[1])      
        try:
            request.urlretrieve(self.file_location, abs_dest_file_name)
            if not os.path.isfile(abs_dest_file_name):
                return 'remote file does not exist'
            return True
        except IOError:
            return 'Error downloading file'

### ____________________________ Interface ____________________________ ###
class UpdateView(Tk):
    def __init__(self, title: str = "Software update", CancelButton: str = "Cancelar", imgLink: str = None, *args, **kwargs):
        Tk.__init__(self, *args, **kwargs)
        self.wm_title(title)
        self.tk.call('wm', 'iconphoto', self._w, PhotoImage(data=LMUpdate_Ico_base_64_encoded_gif))
        if imgLink:
            _img = PhotoImage(file=imgLink)
        else:
            _img = PhotoImage(data=LMUpdate_base_64_encoded_gif)
        _PhotoLabel = Label(self, image = _img)
        _PhotoLabel.image = _img
        _PhotoLabel.pack()
        self.StatusLabel = Label(self, text="")
        self.StatusLabel.pack(padx=10, pady=10, anchor="w")
        _pb_bt_F = Frame(self)
        _pb_bt_F.pack(fill="x", pady=(0,10))
        _ProgressBar = Progressbar(_pb_bt_F, orient='horizontal', mode='indeterminate')
        _ProgressBar.pack(side="left", fill="x", expand=True, padx=10)
        _ProgressBar.start()
        self._StopButton = Button(_pb_bt_F, text=CancelButton, command=self.CancelUpdate)
        self._StopButton.pack(side="right", padx=10)

        self.mainloop()

    def CancelUpdate(self):
        self._StopButton.config(state="disabled")
        self.UpdateStatus("Tentando cancelar a atualização, aguarde...")
    
    def UpdateStatus(self, status: str):
        self.StatusLabel.config(text= status)
        self.update()

class UpdadeQuestion(Tk):
    def __init__(self,  title: str = "Atualização de software",Message: str = "Temos uma nova atualização disponível!", Question: str = "Você gostaria de atualizar agora?", ButtonYes: str = "Sim", ButtonNo: str = "Não", *args, **kwargs):
        Tk.__init__(self, *args, **kwargs)
        self.wm_title(title)
        self.tk.call('wm', 'iconphoto', self._w, PhotoImage(data=LMUpdate_Ico_base_64_encoded_gif))
        self.attributes('-topmost', True)
        self.UserWantsToUpdate = False
        _CustonMessage = Label(self, text=Message)
        _CustonMessage.pack(padx=20, pady=(20,5))
        _QuestionLabel = Label(self, text=Question)
        _QuestionLabel.pack(padx=20)
        _ButtonsFrame = Frame(self)
        _ButtonsFrame.pack(pady=(20))
        _ButtonYes = Button(_ButtonsFrame, text=ButtonYes, command=lambda answer = True: self.RegUserAnswer(answer))
        _ButtonYes.pack(side="left", padx=10)
        _ButtomNo = Button(_ButtonsFrame, text=ButtonNo, command=lambda answer = False: self.RegUserAnswer(answer))
        _ButtomNo.pack(side="right",padx=10)

        self.mainloop()

    def RegUserAnswer(self, answer):
        self.UserWantsToUpdate = answer
        self.destroy()      

### ____________________________ Update ____________________________ ###



### ____________________________ LIBs ____________________________ ###
class KThread(Thread):
  """A subclass of threading.Thread, with a kill()
method.
    Usage:
         - create a new Thread:
        task = KThread(target=executeChanges, args=(validate, self, whatToDO))
        task.start()
         - To cancel the thread:
        self.task.kill()
        self.task.join()
"""
  def __init__(self, *args, **keywords):
    Thread.__init__(self, *args, **keywords)
    self.killed = False
    
  def start(self):
    """Start the thread."""
    self.__run_backup = self.run
    self.run = self.__run     
    Thread.start(self)
    
  def __run(self):
    """Hacked run function, which installs the
trace."""
    settrace(self.globaltrace)
    self.__run_backup()
    self.run = self.__run_backup
    
  def globaltrace(self, frame, why, arg):
    if why == 'call':
      return self.localtrace
    else:
      return None
      
  def localtrace(self, frame, why, arg):
    if self.killed:
      if why == 'line':
        raise SystemExit()
    return self.localtrace
    
  def kill(self):
    self.killed = True

### ____________________________ Image ____________________________ ###
LMUpdate_base_64_encoded_gif = b'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'
LMUpdate_Ico_base_64_encoded_gif = b'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'


### ____________________________ Init ____________________________ ###
if __name__ == "__main__":
    UpdateView()