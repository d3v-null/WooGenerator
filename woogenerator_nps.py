import logging
from pprint import pprint

# import npyscreen
from npyscreen import NPSAppManaged, Form
from npyscreen import TitleText, TitleSelectOne, MultiLine

class WelcomeForm(Form):
    def create(self):
        self.sync_subjects = self.add(
            MultiLine,
            scroll_exit=True,
            name="Sync Type",
            values=[
                'products',
                'customers'
            ]
        )

    def afterEditing(self):
        self.parentApp.setNextForm(None)

class WooGenerator(NPSAppManaged):
    def onStart(self):
        self.addForm('MAIN', WelcomeForm, name="Welcome")

if __name__ == "__main__":
    logging.basicConfig(filename="woogenerator.log", level=logging.DEBUG)
    wgApp = WooGenerator()
    logging.info("wgApp._Forms: %s", pprint(wgApp._Forms))
    wgApp.run()

