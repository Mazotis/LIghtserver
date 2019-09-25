#!/usr/bin/env python3
'''
    File name: backup.py
    Author: Maxime Bergeron
    Date last modified: 25/09/2019
    Python Version: 3.5

    A backup manager/rsync wrapper module for the homeserver
'''

import os
import shlex
import signal
import subprocess
import time
from datetime import datetime, timedelta
from devices.common import *
from threading import Thread, Event

class backup(Thread):
    def __init__(self, config, lm):
        Thread.__init__(self)
        self.config = config
        self.lm = lm
        self.backup_interval = config["BACKUP"].getint("DELAY_BETWEEN_BACKUPS")
        self.backup_server = config["BACKUP"]["BACKUP_SERVER"]
        self.backup_server_forceon = config["BACKUP"].getboolean("BACKUP_SERVER_FORCE_ON")
        self.stopevent = Event()
        self.last_backup = 0
        self.running = True
        self.rsync = None

    def run(self):
        debug.write("Starting backup manager", 0, "BACKUP")
        if self.backup_server != "local": 
            if int(self.backup_server) > len(self.lm.devices):
                debug.write("DEVICE{} is not valid. Quitting module".format(self.backup_server), 2, "BACKUP")
                self.stop()
                return
            if self.lm.devices[int(self.backup_server)].device_type != "Computer":
                debug.write("DEVICE{} ({}) is not listed as Computer device in the Devicemanager. Quitting module"
                            .format(self.backup_server, self.lm.devices[int(self.backup_server)].name), 2, "BACKUP")
                self.stop()
                return

        self.run_backup()
        _next_run = self.last_backup + timedelta(hours=self.backup_interval)
        debug.write("Will do another backup at: {}".format(_next_run.strftime('%d %B, %H:%M')), 
                                                                   0, "BACKUP")
        while not self.stopevent.is_set():
            if _next_run > datetime.datetime.now():
                self.stopevent.wait(600)
                continue
            self.run_backup()
            _next_run = self.last_backup + timedelta(hours=self.backup_interval)
            debug.write("Will do another backup at: {}".format(_next_run.strftime('%d %B, %H:%M')), 
                                                               0, "BACKUP")
        self.stop()
        return

    def run_backup(self):
        self.last_backup = datetime.datetime.now()
        debug.write("Starting backups", 0, "BACKUP")
        backup_server = None
        server_was_off = False
        if self.backup_server != "local":
            backup_server = self.lm.devices[int(self.backup_server)]
            if str(backup_server.get_state()) != DEVICE_ON:
                if self.config["BACKUP"].getboolean("BACKUP_SERVER_FORCE_ON"):
                    server_was_off = True
                    debug.write("Turning on backup server", 0, "BACKUP")
                    _col = ["-1"] * len(self.lm.devices)
                    _col[int(self.backup_server)] = "1"
                    self.lm.set_colors(_col)
                    self.lm.set_skip_time_check()
                    self.lm.set_mode(False,False)
                    self.lm.run()
                    while str(backup_server.get_state()) != DEVICE_ON:
                        debug.write("Waiting for backup server...", 0, "BACKUP")
                        self.stopevent.wait(5)
                else:
                    debug.write("Backup server is offline and no FORCE_ON. Reporting backups.", 0, "BACKUP")
                    return

        i = 0
        while self.running:
            try:
                destination = ""
                if self.config["BACKUP"]["CLIENT" + str(i)] != "local":
                    client = self.lm.devices[self.config["BACKUP"].getint("CLIENT" + str(i))]
                    client_was_off = False
                    if str(client.get_state()) != DEVICE_ON:
                        if self.config["BACKUP"].getboolean("CLIENT" + str(i) +"_FORCE_ON"):
                            client_was_off = True
                            debug.write("Turning ON CLIENT{}".format(i), 0, "BACKUP")
                            _col = ["-1"] * len(self.lm.devices)
                            _col[self.config["BACKUP"].getint("CLIENT" + str(i))] = "1"
                            self.lm.set_colors(_col)
                            self.lm.set_skip_time_check()
                            self.lm.set_mode(False,False)
                            self.lm.run()
                            while str(client.get_state()) != DEVICE_ON:
                                debug.write("Waiting for client...", 0, "BACKUP")
                                self.stopevent.wait(5)
                        else:
                            debug.write("Skipping CLIENT{}, device is offline.".format(i), 0, "BACKUP")
                            i = i + 1
                            continue

                debug.write('Backing up client: {}'.format(client.name), 0, "BACKUP")
                if self.backup_server != "local" and self.backup_server != self.config["BACKUP"]["CLIENT" + str(i)]:
                    destination = "{}@{}:{}".format(backup_server.user, backup_server.ip, self.config["BACKUP"]["CLIENT" + str(i) + "_DESTINATION"])
                else:
                    destination = self.config["BACKUP"]["CLIENT" + str(i) + "_DESTINATION"]

                folders = []
                folders = self.config["BACKUP"]["CLIENT" + str(i) + "_FOLDERS"].split(",")
                for _folder in folders:
                    command = ""
                    if self.config["BACKUP"].getboolean("CLIENT" + str(i) + "_DELETE"):
                        command = "/usr/bin/rsync -az --delete"
                    else:
                        command = "/usr/bin/rsync -az"
                    if client == "local":
                        command = "{} {} {}".format(command, _folder, destination)
                    else:
                        if self.backup_server != "local":
                            command = "/usr/bin/ssh -t {}@{} '{} {} {}'".format(client.user, client.ip, command, _folder, destination)
                        else:
                            command = "{} {}@{}:{} {}".format(command, client.user, client.ip, _folder, destination)

                    debug.write('Backing up folder {}'.format(_folder), 0, "BACKUP")
                    debug.write('Running rsync command: {}'.format(command), 0, "BACKUPS")
                    
                    #TODO handle keyboardinterrupts properly ?
                    self.rsync = subprocess.Popen(shlex.split(command), stdout=None, 
                                                      preexec_fn=os.setsid)
                    self.rsync.wait()
                    self.rsync = None
                    if not self.running:
                        return

                if client_was_off:
                    debug.write("Turning back OFF CLIENT{}".format(i), 0, "BACKUP")
                    _col = ["-1"] * len(self.lm.devices)
                    _col[self.config["BACKUP"].getint("CLIENT" + str(i))] = "0"
                    self.lm.set_colors(_col)
                    self.lm.set_skip_time_check()
                    self.lm.set_mode(False,False)
                    self.lm.run()

            except KeyError as ex:
                debug.write('Backups are done', 0, "BACKUP")
                break

            i = i + 1

        if server_was_off:
            debug.write("Turning back OFF backup server".format(i), 0, "BACKUP")
            _col = ["-1"] * len(self.lm.devices)
            _col[int(self.backup_server)] = "0"
            self.lm.set_colors(_col)
            self.lm.set_skip_time_check()
            self.lm.set_mode(False,False)
            self.lm.run()

        return

    def stop(self):
        debug.write("Stopping.", 0, "BACKUP")
        self.running = False
        if self.rsync is not None:
            debug.write("Killing remaining backup.", 0, "BACKUP")
            os.killpg(os.getpgid(self.rsync.pid), signal.SIGTERM)
        self.stopevent.set()
        pass
