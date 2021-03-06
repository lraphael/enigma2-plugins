##
## PasswordChanger
## by AliAbdul
##
from Components.ActionMap import ActionMap
from Components.config import config, ConfigText, ConfigSubsection, getConfigListEntry
from Components.ConfigList import ConfigListScreen
from Components.Language import language
from Components.ScrollLabel import ScrollLabel
from os import environ
from Plugins.Plugin import PluginDescriptor
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from telnetlib import Telnet
from Tools.Directories import resolveFilename, SCOPE_LANGUAGE, SCOPE_PLUGINS
import gettext

############################################

def localeInit():
	lang = language.getLanguage()
	environ["LANGUAGE"] = lang[:2]
	gettext.bindtextdomain("enigma2", resolveFilename(SCOPE_LANGUAGE))
	gettext.textdomain("enigma2")
	gettext.bindtextdomain("PasswordChanger", "%s%s" % (resolveFilename(SCOPE_PLUGINS), "Extensions/PasswordChanger/locale/"))

def _(txt):
	t = gettext.dgettext("PasswordChanger", txt)
	if t == txt:
		t = gettext.gettext(txt)
	return t

localeInit()
language.addCallback(localeInit)

############################################

config.plugins.PasswordChanger = ConfigSubsection()
config.plugins.PasswordChanger.old_password = ConfigText(default="", fixed_size=False)
config.plugins.PasswordChanger.new_password = ConfigText(default="", fixed_size=False)

############################################

class PasswordChanger(ConfigListScreen, Screen):
	skin = """
		<screen position="center,center" size="420,70" title="%s" >
			<widget name="config" position="0,0" size="420,70" scrollbarMode="showOnDemand" />
		</screen>""" % _("Password Changer")

	def __init__(self, session, args=None):
		Screen.__init__(self, session)
		self.session = session
		
		ConfigListScreen.__init__(self, [
		getConfigListEntry(_("Old password:"), config.plugins.PasswordChanger.old_password),
		getConfigListEntry(_("New password:"), config.plugins.PasswordChanger.new_password)])
		
		self["actions"] = ActionMap(["OkCancelActions"], {"ok": self.changePassword, "cancel": self.exit}, -2)

	def changePassword(self):
		old_pass = config.plugins.PasswordChanger.old_password.value
		new_pass = config.plugins.PasswordChanger.new_password.value
		
		if len(new_pass) > 4 and len(new_pass) < 9:
			self.session.open(PasswordChangerConsole, old_pass, new_pass)
		else:
			self.session.open(MessageBox, _("Incorrect new password!\nMinimum length: 5\nMaximum length: 8"), MessageBox.TYPE_ERROR)

	def exit(self):
		for x in self["config"].list:
			x[1].cancel()
		
		self.close()

############################################

class PasswordChangerConsole(Screen):
	skin = """
		<screen position="center,center" size="520,400" title="%s" >
			<widget name="label" position="0,0" size="520,400" font="Regular;20" />
		</screen>""" % _("Password Changer")

	def __init__(self, session, old_pass, new_pass):
		Screen.__init__(self, session)
		
		self.working = True
		self.old_pass = old_pass
		self.new_pass = new_pass
		self.log = ""
		self.timeout = 2
		
		self["label"] = ScrollLabel("")
		
		self["actions"] = ActionMap(["WizardActions"],
			{
				"ok": self.exit,
				"back": self.exit,
				"up": self["label"].pageUp,
				"down": self["label"].pageDown,
				"left": self["label"].pageUp,
				"right": self["label"].pageDown
			}, -1)
		
		self.onLayoutFinish.append(self.run)

	def exit(self):
		if not self.working:
			self.sendMessage("exit")
			self.close()

	def sendMessage(self, message):
		if self.t is not None:
			self.t.write(message + "\n")
			r = self.t.read_until("UNKNOWN", self.timeout)
			self.log += r
			return r
		else:
			return ""

	def run(self):
		logged_in = False
		
		try:
			self.t = Telnet("localhost")
			
			self.log = self.t.read_until("login:", self.timeout)
			if self.log.__contains__("login:"):
				r = self.sendMessage("root")
				if r.__contains__("~#"):
					logged_in = True
				
				elif r.__contains__("Password:"):
					r = self.sendMessage(self.old_pass)
					if r.__contains__("~#"):
						logged_in = True
		except:
			self.t = None
		
		if logged_in:
			self.changePassword()
		else:
			self.log += _("Could not log in!")
			self["label"].setText(self.log)
			self.working = False

	def changePassword(self):
		try:
			r = self.sendMessage("passwd")
			if r.__contains__("Enter new password:") or r.__contains__("New password:"):
				r = self.sendMessage(self.new_pass)
				
				if r.__contains__("Re-enter new password:") or r.__contains__("Retype password:"):
					r = self.sendMessage(self.new_pass)
		except:
			self.log += _("Error while setting new password!")
		
		self["label"].setText(self.log)
		self.working = False

############################################

def start(session, **kwargs):
	session.open(PasswordChanger)

def main(menuid):
	if menuid != "system": 
		return [ ]
	return [(_("Password Changer"), start, "password_changer", None)]

############################################

def Plugins(**kwargs):
	return PluginDescriptor(name=_("Password Changer"), description=_("Change your ftp and telnet password"), where=PluginDescriptor.WHERE_MENU, fnc=main)
