import logging
from pprint import pprint

# import npyscreen
from npyscreen import NPSAppManaged
from npyscreen import Form, ActionForm
from npyscreen import TitleText, TitleSelectOne, MultiLine, MultiLineEdit

class ProductsForm(ActionForm):
    def create(self):
        self.add(
            MultiLineEdit,
            editable=False,
            max_height=10,
            max_width=70,
            value="Products"
        )

class CustomersForm(ActionForm):
    def create(self):
        self.add(
            MultiLineEdit,
            editable=False,
            max_height=10,
            max_width=70,
            value="Customers"
        )

class WelcomeForm(ActionForm):
    formOptions = {
        'products':'PRODUCTS',
        'customers':'CUSTOMERS'
    }

    def create(self):
        self.add(
            MultiLineEdit,
            editable=False,
            max_height=10,
            max_width=70,
            value= \
" _______ _______ __   _ _______ __   __ __   _ _______\n" +
"    |    |_____| | \  | |______   \_/   | \  | |\n" +
"    |    |     | |  \_| ______|    |    |  \_| |_____\n" +
"\n" +
"Welcome to the TanSync Utility.\n" +
"\n" +
"What would you like to sync?\n"
        )
        self.sync_subject = self.add(
            MultiLine,
            scroll_exit=True,
            name="Sync Type",
            values=self.formOptions.keys()
        )

    def afterEditing(self):
        sync_subject = (self.sync_subject.values[ self.sync_subject.value ])
        logging.info("Sync Subject Value: %s", sync_subject)
        next_form = self.formOptions.get(sync_subject)
        logging.info("setting next form to %s" , next_form)
        self.parentApp.setNextForm(next_form)

class WooGenerator(NPSAppManaged):
    def onStart(self):
        self.addForm(
            'MAIN',
            WelcomeForm,
            name="Welcome",
            # columns=80,
        )
        self.addForm(
            'PRODUCTS',
            ProductsForm,
            name="Products"
        )
        self.addForm(
            'CUSTOMERS',
            CustomersForm,
            name='Customers'
        )

if __name__ == "__main__":
    logging.basicConfig(filename="woogenerator.log", level=logging.DEBUG)
    wgApp = WooGenerator()
    wgApp.run()

