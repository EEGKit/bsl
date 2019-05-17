#!/usr/bin/env python
#coding:utf-8

"""
  Author:  Arnaud Desvachez --<arnaud.desvachez@gmail.com>
  Purpose: Defines the mainWindow class for the PyCNBI GUI.
  Created: 2/22/2019
"""

import sys
from importlib import import_module, reload
from os.path import expanduser
from queue import Queue
import os 
import inspect

from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog, QAction, QLabel, QVBoxLayout, QHBoxLayout, QComboBox, QLineEdit, QFormLayout, QWidget, QPushButton, QFrame, QSizePolicy
from PyQt5.QtCore import pyqtSignal, pyqtSlot, QThread, QLine
from PyQt5.QtGui import QTextCursor, QFont

from ui_mainwindow import Ui_MainWindow
from streams import WriteStream, MyReceiver
from connectClass import PathFolderFinder, PathFileFinder, Connect_Directions, Connect_ComboBox, Connect_LineEdit, Connect_SpinBox, Connect_DoubleSpinBox, Connect_Modifiable_List, Connect_Modifiable_Dict
from pickedChannelsDialog import PickChannelsDialog, Channel_Select

from pycnbi.triggers.trigger_def import trigger_def

DEFAULT_PATH = os.environ['PYCNBI_SCRIPTS']


########################################################################
class MainWindow(QMainWindow):
    """
    Defines the mainWindow class for the PyCNBI GUI.
    """
    #----------------------------------------------------------------------
    def __init__(self):
        """
        Constructor.
        """
        super(MainWindow, self).__init__()

        self.cfg_struct = None      # loaded module containing all param possible values
        self.cfg_subject = None     # loaded module containing subject specific values
        self.paramsWidgets = {}     # dict of all the created parameters widgets

        self.load_ui_from_file()
        self.redirect_stdout()
        self.connect_signals_to_slots()

        # Terminal
        self.ui.textEdit_terminal.setReadOnly(1)
        font = QFont()
        font.setPointSize(10)
        self.ui.textEdit_terminal.setFont(font)

    # ----------------------------------------------------------------------
    def redirect_stdout(self):
        """
        Create Queue and redirect sys.stdout to this queue.
        Create thread that will listen on the other end of the queue, and send the text to the textedit_terminal.
        """
        queue = Queue()
        sys.stdout = WriteStream(queue)
        sys.stderr = WriteStream(queue)
        
        self.thread = QThread()
        self.my_receiver = MyReceiver(queue)
        self.my_receiver.mysignal.connect(self.on_terminal_append)
        self.my_receiver.moveToThread(self.thread)
        self.thread.started.connect(self.my_receiver.run)
        self.thread.start()
        
        
    #----------------------------------------------------------------------
    def load_ui_from_file(self):
        """
        Loads the UI interface from file.
        """
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        
        
    #----------------------------------------------------------------------
    def clear_params(self):
        """
        Clear all previously loaded params widgets.
        """
        
        if self.ui.scrollAreaWidgetContents_Basics.layout() != None:
            QWidget().setLayout(self.ui.scrollAreaWidgetContents_Adv.layout())
            QWidget().setLayout(self.ui.scrollAreaWidgetContents_Basics.layout())

            
    # ----------------------------------------------------------------------
    def extract_value_from_module(self, key, values):
        """
        Extracts the subject's specific value associated with key.
        key = parameter name.
        values = list of all the parameters values. 
        """
        for v in values:
            if v[0] == key:
                return v[1]

    # ----------------------------------------------------------------------
    def load_channels_from_txt(self):
        """
        Loads the channels list from a txt file.
        """
        filePath = self.ui.lineEdit_pathSearch.text()
        file = open(filePath + "/channelsList.txt")
        channels = file.read().splitlines()
        file.close()
        
        return channels

    # ----------------------------------------------------------------------
    def disp_params(self, cfg_template_module, cfg_module):
        """
        Displays the parameters in the corresponding UI scrollArea.
        cfg = config module
        """

        self.clear_params()
        # Extract the parameters and their possible values from the template modules.
        params = inspect.getmembers(cfg_template_module)

        # Extract the chosen values from the subject's specific module.
        all_chosen_values = inspect.getmembers(cfg_module)

        # Load channels
        self.channels = self.load_channels_from_txt()

        # Iterates over the classes
        for par in range(2):
            param = inspect.getmembers(params[par][1])
            # Create layouts            
            layout = QFormLayout()

            # Iterates over the list
            for p in param:
                # Remove useless attributes
                if '__' in p[0]:
                    continue
                
                # Iterates over the dict
                for key, values in p[1].items():
                    chosen_value = self.extract_value_from_module(key, all_chosen_values)

                    # For the feedback directions [offline and online].
                    if 'DIRECTIONS' in key:
                        nb_directions = 4
                        directions = Connect_Directions(key, chosen_value, values, nb_directions)
                        directions.signal_paramChanged.connect(self.on_guichanges)
                        self.paramsWidgets.update({key: directions})
                        layout.addRow(key, directions.l)

                    # For providing a folder path.
                    elif 'PATH' in key:
                        pathfolderfinder = PathFolderFinder(key, DEFAULT_PATH, chosen_value)
                        pathfolderfinder.signal_pathChanged.connect(self.on_guichanges)
                        self.paramsWidgets.update({key: pathfolderfinder})
                        layout.addRow(key, pathfolderfinder.layout)
                        continue

                    # For providing a file path.
                    elif 'FILE' in key:
                        pathfilefinder = PathFileFinder(key, chosen_value)
                        pathfilefinder.signal_pathChanged.connect(self.on_guichanges)
                        self.paramsWidgets.update({key: pathfilefinder})
                        layout.addRow(key, pathfilefinder.layout)
                        continue

                    # For the special case of choosing the trigger classes to train on [trainer only]
                    elif 'TRIGGER_DEF' in key:
                        trigger_file = self.extract_value_from_module('TRIGGER_FILE', all_chosen_values)
                        tdef = trigger_def(trigger_file)
                        nb_directions = 4
                        directions = Connect_Directions(key, chosen_value, list(tdef.by_name), nb_directions)
                        directions.signal_paramChanged.connect(self.on_guichanges)
                        self.paramsWidgets.update({key: directions})
                        layout.addRow(key, directions.l)
                        continue

                    # To select specific electrodes
                    elif '_CHANNELS' in key or 'CHANNELS_' in key:
                        ch_select = Channel_Select(key, self.channels, chosen_value)
                        ch_select.signal_paramChanged.connect(self.on_guichanges)
                        self.paramsWidgets.update({key: ch_select})
                        layout.addRow(key, ch_select.layout)

                    # For all the int values.
                    elif values is int:
                        spinBox = Connect_SpinBox(key, chosen_value)
                        spinBox.signal_paramChanged.connect(self.on_guichanges)
                        self.paramsWidgets.update({key: spinBox})
                        layout.addRow(key, spinBox.w)
                        continue

                    # For all the float values.
                    elif values is float:
                        doublespinBox = Connect_DoubleSpinBox(key, chosen_value)
                        doublespinBox.signal_paramChanged.connect(self.on_guichanges)
                        self.paramsWidgets.update({key: doublespinBox})
                        layout.addRow(key, doublespinBox.w)
                        continue

                    # For parameters with multiple non-fixed values in a list (user can modify them)
                    elif values is list:
                        modifiable_list = Connect_Modifiable_List(key, chosen_value, values)
                        modifiable_list.signal_paramChanged[str, list].connect(self.on_guichanges)
                        self.paramsWidgets.update({key: modifiable_list})
                        layout.addRow(key, modifiable_list.hlayout)
                        continue

                    # For parameters with multiple fixed values.
                    elif type(values) is tuple:
                        comboParams = Connect_ComboBox(key, chosen_value, values)
                        comboParams.signal_paramChanged[str, bool].connect(self.on_guichanges)
                        comboParams.signal_paramChanged[str, list].connect(self.on_guichanges)
                        comboParams.signal_paramChanged[str, str].connect(self.on_guichanges)
                        comboParams.signal_paramChanged[str, type(None)].connect(self.on_guichanges)
                        self.paramsWidgets.update({key: comboParams})
                        layout.addRow(key, comboParams.templateChoices)
                        continue
                    
                    # For parameters with multiple non-fixed values in a dict (user can modify them)
                    elif type(values) is dict:
                        modifiable_dict = Connect_Modifiable_Dict(key, chosen_value, values)
                        modifiable_dict.signal_paramChanged[str, dict].connect(self.on_guichanges)
                        self.paramsWidgets.update({key: modifiable_dict})
                        layout.addRow(key, modifiable_dict.layout)
                        continue


                # Add a horizontal line to separate parameters' type.
                if p != param[-1]:
                    separator = QFrame()
                    separator.setFrameShape(QFrame.HLine)
                    separator.setFrameShadow(QFrame.Sunken)
                    layout.addRow(separator)

                # Display the parameters according to their types.
                if params[par][0] == 'Basic':
                    self.ui.scrollAreaWidgetContents_Basics.setLayout(layout)
                elif params[par][0] == 'Advanced':
                    self.ui.scrollAreaWidgetContents_Adv.setLayout(layout)


    # ----------------------------------------------------------------------
    def load_config(self, cfg_path, cfg_file, subj_file):
        """
        Dynamic loading of a config file.
        Format the lib to fit the previous developed pycnbi code if subject specific file (not for the templates).
        cfg_path: path to the folder containing the config file.
        cfg_file: config file to load.
        subj_file: true or false, if true it means it is the subject specific file. Format it.
        """
        if self.cfg_subject == None or cfg_file not in self.cfg_subject.__file__:
            # Dynamic loading
            sys.path.append(cfg_path)
            cfg_module = import_module(cfg_file)
        else:
            cfg_module = reload(self.cfg_subject)
        # Format the lib to fit the previous developed pycnbi code if subject specific file.
        # if subj_file:
            # self.cfg = type('cfg', (cfg_module.Advanced, cfg_module.Basic), dict())

        return cfg_module
        
    #----------------------------------------------------------------------
    def load_all_params(self, cfg_template, cfg_file):
        """
        Loads the params structure and assign the subject/s specific value.
        It also checks the sanity of the loaded params according to the protocol.
        """
        
        # Loads the template
        if self.cfg_struct == None or cfg_template not in self.cfg_struct.__file__:
            self.cfg_struct = self.load_struct_params(cfg_template)
        
        # Loads the subject's specific values
        self.cfg_subject = self.load_subject_params(cfg_file)
        
        # Check the parameters integrity
        self.cfg_subject = self.m.check_config(self.cfg_subject)
        
        # Display parameters on the GUI
        self.disp_params(self.cfg_struct, self.cfg_subject)
        self.cfg_struct

    # ----------------------------------------------------------------------
    def load_struct_params(self, cfg_template):
        """
        Load the parameters' structure from file depending on the choosen protocol.
        """
        cfg_template_path = os.environ['PYCNBI_ROOT']+'\pycnbi\config_files'
        cfg_template_module  = self.load_config(cfg_template_path, cfg_template, False) 
        return cfg_template_module
        
    
    #----------------------------------------------------------------------
    def load_subject_params(self, cfg_file):
        """
        Loads the subject specific parameters' values from file and displays them.
        cfg_file: config file to load.
        """
        cfg_path = self.ui.lineEdit_pathSearch.text()+'/python'
        cfg_module  = self.load_config(cfg_path, cfg_file, True)               
        return cfg_module


    @pyqtSlot(str, str)
    @pyqtSlot(str, bool)
    @pyqtSlot(str, list)
    @pyqtSlot(str, float)
    @pyqtSlot(str, int)
    @pyqtSlot(str, dict)
    @pyqtSlot(str, type(None))
    # ----------------------------------------------------------------------
    def on_guichanges(self, name, new_Value):
        """
        Apply the modification to the corresponding param of the cfg module
        
        name = parameter name
        new_value = new str value to to change in the module 
        """
        setattr(self.cfg_subject, name, new_Value)
        print(getattr(self.cfg_subject, name))


    # ----------------------------------------------------------------------
    @pyqtSlot()
    def on_click_pathSearch(self):
        """
        Opens the File dialog window when the search button is pressed.
        """
        path_name = QFileDialog.getExistingDirectory(caption="Choose the subject's directory", directory=DEFAULT_PATH)
        self.ui.lineEdit_pathSearch.insert(path_name)


    # ----------------------------------------------------------------------
    @pyqtSlot()
    def on_click_offline(self):
        """ 
        Loads the Offline parameters. 
        """
        import pycnbi.protocols.train_mi as m
        self.m = m
        cfg_template = 'config_structure_train_mi'
        cfg_file = 'config_train_mi'
        self.load_all_params(cfg_template, cfg_file)


    #----------------------------------------------------------------------
    @pyqtSlot()
    def on_click_train(self):
        """
        Loads the Training parameters.
        """
        import pycnbi.decoder.trainer as m
        self.m = m
        cfg_template = 'config_structure_trainer_mi'
        cfg_file = 'config_trainer_mi'
        self.load_all_params(cfg_template, cfg_file)
        
        
    #----------------------------------------------------------------------
    @pyqtSlot()
    def on_click_online(self):
        """
        Loads the Online parameters.
        """
        import pycnbi.protocols.test_mi as m
        self.m = m
        cfg_template = 'config_structure_test_mi'
        cfg_file = 'config_test_mi'
        self.load_all_params(cfg_template, cfg_file)
    
    
    #----------------------------------------------------------------------v
    @pyqtSlot()
    def on_click_start(self):
        """
        Launch the selected protocol. It can be Offline, Train or Online. 
        """
        self.m.run(self.cfg_subject)
        
    #----------------------------------------------------------------------
    @pyqtSlot(str)
    def on_terminal_append(self, text):
        """
        Writes to the QtextEdit_terminal the redirected stdout.
        """
        self.ui.textEdit_terminal.moveCursor(QTextCursor.End)
        self.ui.textEdit_terminal.insertPlainText(text)

        
    #----------------------------------------------------------------------
    def connect_signals_to_slots(self):
        """Connects the signals to the slots"""
        # Search  folder button
        self.ui.pushButton_Search.clicked.connect(self.on_click_pathSearch)
        # Offline button
        self.ui.pushButton_Offline.clicked.connect(self.on_click_offline)
        # Train button
        self.ui.pushButton_Train.clicked.connect(self.on_click_train)
        # Online button
        self.ui.pushButton_Online.clicked.connect(self.on_click_online)
        # Start button
        self.ui.pushButton_Start.clicked.connect(self.on_click_start)
        
def main():    
    #unittest.main()
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()