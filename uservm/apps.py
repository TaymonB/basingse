from django.apps import AppConfig

class UserVMConfig(AppConfig):

    name = 'uservm'
    verbose_name = 'User VM Manager'

    #def ready(self):
    #    from uservm import signals
