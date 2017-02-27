# -*- coding: utf-8 -*-

import logging
# from pprint import pprint
import contextlib
from collections import namedtuple, OrderedDict

import npyscreen
# from npyscreen import NPSAppManaged
# from npyscreen import Form, AProductsFormctionForm
# from npyscreen import TitleText, TitleSelectOne, MultiLine, MultiLineEdit

ScreenOffset = namedtuple('Offset', ['col', 'row'])

class WooGenerator(npyscreen.NPSAppManaged):
    PRODUCTS_FORM_ID = "PRODUCTS"
    CUSTOMERS_FORM_ID = 'CUSTOMERS'
    CONFIRM_FORM_ID = 'CONFIRM'

    def onStart(self):
        self.addForm(
            'MAIN',
            WelcomeForm,
            name="Welcome",
        )

        self.addForm(
            self.__class__.PRODUCTS_FORM_ID,
            ProductsForm,
            name="Products"
        )

        self.addForm(
            self.__class__.CUSTOMERS_FORM_ID,
            CustomersForm,
            name='Customers'
        )

        self.addForm(
            self.__class__.CONFIRM_FORM_ID,
            ConfirmForm,
            name='Confirmation'
        )


class SyncForm(npyscreen.ActionFormV2):
    BUTTON_META = OrderedDict( [
            (
                'ok_button',{
                    'text':npyscreen.ActionFormV2.OK_BUTTON_TEXT,
                    'type':npyscreen.ActionFormV2.OKBUTTON_TYPE,
                }
            ),
            (
                'cancel_button',{
                    'text':npyscreen.ActionFormV2.CANCEL_BUTTON_TEXT,
                    'type':npyscreen.ActionFormV2.CANCELBUTTON_TYPE
                }
            )
    ])

    IGNORE_BUTTONS = []

    def create_control_buttons(self):
        current_b_offset = 1
        current_r_offset = 6
        for button_name, button_meta in self.__class__.BUTTON_META.items():
            logging.info("%s ignore buttons: %s", self.__class__,
                         self.__class__.IGNORE_BUTTONS)
            if button_name in self.__class__.IGNORE_BUTTONS:
                logging.info("%s ignoring button: %s", self.__class__, button_name)
                continue
            button_text = button_meta.get('text', '')
            button_br_offset = ScreenOffset(
                0 - current_r_offset - len(button_text),
                0 - current_b_offset
            )

            button_type = button_meta.get('type',
                                          self.__class__.CANCELBUTTON_TYPE)

            logging.info("%s creating button: %s", self.__class__, button_name)

            self._add_button(
                button_name,
                button_type,
                button_text,
                button_br_offset.row,
                button_br_offset.col,
                None
            )

            current_r_offset += 4 + len(button_text)




    def find_cancel_button(self):
        assert npyscreen.ActionFormV2.CANCEL_BUTTON_TEXT in self.__class__.BUTTONS
        button_index = self.__class__.BUTTONS.index(npyscreen.ActionFormV2.CANCEL_BUTTON_TEXT)
        self.editw = len(self._widgets__) - 2 - button_index


    def on_cancel(self):
        logging.info("performing cancel")
        self.parentApp.switchFormPrevious()

    welcomeLines = [
    ]

    def addSingleLine(self, line, **kwargs):
        field_kwargs = dict(
            editable=False,
            value=line
        )
        field_kwargs.update(**kwargs)
        self.add(
            npyscreen.Textfield,
            **field_kwargs
        )

    def addParagraph(self, lines, **kwargs):
        padding = kwargs.pop('padding', 1)
        if lines:
            if lines[-1] and padding:
                for i in range(padding):
                    lines.append('')
            for line in lines:
                self.addSingleLine(line, **kwargs)

    def addSimpleQuestion(self, name=None, help_str=None, default=None,
                          answers=None, indent=1):

        if answers is None:
            answers=["No", "Yes"]

        if not name:
            name=""

        if help_str:
            self.addParagraph(
                [ help_str ],
                padding=0
            )

        if default is None:
            default=1

        return self.add(
            npyscreen.SelectOne,
            scroll_exit=True,
            name=name,
            values=answers,
            value=default,
            max_height=len(answers) + 1
        )

    def create(self):
        self.addParagraph(self.welcomeLines)

class ProductsForm(SyncForm):
    # welcomeLines = [
    #     "PRODUCTS",
    #     ""
    # ]

    BUTTON_META = SyncForm.BUTTON_META
    BUTTON_META['ok_button']['text'] = 'Next'

    @contextlib.contextmanager
    def increaseIndent(self):
        self.current_indent += 1
        yield
        self.current_indent -= 1

    def create(self):
        self.current_indent = 0

        super(ProductsForm, self).create()

        self.download_master = self.addSimpleQuestion(
            name="Download Master",
            help_str="Has the Google Drive Spreadsheet Been updated recently?",
            default=1
        )

        self.generate_report = self.addSimpleQuestion(
            name="Generate Report",
            help_str="Would you like to generate a sync report? (slow)",
            default=0
        )

        self.process_specials = self.addSimpleQuestion(
            name="Process Specials",
            help_str="How would you like to process specials?",
            answers=[
                "No Specials",
                "Auto Next Special",
                "All Future Specials"
            ],
                     # "Override"],
            default=0
        )

        # with self.increaseIndent():
        #     # indent process_specials questions
        #     self.addParagraph(
        #         ["What is the specials override?"],
        #         hidden=True
        #     )
        #     self.specials_override = self.add(
        #         npyscreen.Textfield,
        #         name="Specials Override",
        #         scroll_exit=True,
        #         hidden=True
        #     )

        self.process_categories = self.addSimpleQuestion(
            name="Process Categories",
            help_str="Would you like to process categories?",
            default=0
        )

        self.process_variations = self.addSimpleQuestion(
            name="Process Variations",
            help_str="Would you like to process variations?",
            default=0
        )

class CustomersForm(SyncForm):
    welcomeLines = [
        "CUSTOMERS"
    ]


    def create(self):
        super(CustomersForm, self).create()

class ConfirmForm(SyncForm):
    pass

class FormSwitcher(npyscreen.MultiLineAction):
    def __init__(self, *args, **kwargs):
        self.formOptions = kwargs.get('formOptions', OrderedDict)
        kwargs.update(
            values=self.formOptions.keys()
        )
        super(FormSwitcher, self).__init__(*args, **kwargs)

    def actionHighlighted(self, act_on_this, key_press):
        logging.info("actionHighlighted: %s %s", act_on_this, key_press)
        next_form = self.formOptions.get(act_on_this)
        logging.info("setting next form to %s" , next_form)
        self.parent.parentApp.setNextForm(next_form)
        self.parent.parentApp.switchFormNow()


class WelcomeForm(SyncForm):
    welcomeLines = [
        # " _______ _______ __   _ _______ __   __ __   _ _______" ,
        # "    |    |_____| | \  | |______   \_/   | \  | |      " ,
        # "    |    |     | |  \_| ______|    |    |  \_| |_____ " ,

        " ██████████████                                  ██████████████",
        " ██          ██ ██████████████ ███████   ██████ ██          ██ ██████  ██████ ███████   ██████ ██████████████ ",
        " ██████  ██████ ██          ██ ██    █  ██  ██ ██  ██████████ █  ██  █ ██    █  ██  ██ ██          ██ ",
        "     ██  ██     ██  ██████  ██ ██    █ ██  ██ ██  ██          █  ██  █  ██    █ ██  ██ ██  ██████████ ",
        "     ██  ██     ██  ██  ██  ██ ██  █  ███  ██ ██  ██████████   █    █   ██  █  ███  ██ ██  ██         ",
        "     ██  ██     ██  ██████  ██ ██  ██  ███  ██ ██          ██    █    █    ██  ██  ███  ██ ██  ██         ",
        "     ██  ██     ██          ██ ██  ███  ██  ██ ██████████  ██     █  █     ██  ███  ██  ██ ██  ██         ",
        "     ██  ██     ██  ██████  ██ ██  ███  █  ██         ██  ██      ██  ██      ██  ███  █  ██ ██  ██         ",
        "     ██  ██     ██  ██  ██  ██ ██  ██ █    ██         ██  ██      ██  ██      ██  ██ █    ██ ██  ██         ",
        "     ██  ██     ██  ██  ██  ██ ██  ██  █    ██ ██████████  ██      ██  ██      ██  ██  █    ██ ██  ██████████ ",
        "     ██  ██     ██  ██  ██  ██ ██  ██   █   ██ ██          ██      ██  ██      ██  ██   █   ██ ██          ██ ",
        "     ██████     ██████  ██████ ██████    ██████ ██████████████      ██████      ██████    ██████ ██████████████ ",
        "" ,
        "Welcome to the TanSync Utility." ,
        "" ,
        "What would you like to sync?",
        ""
    ]

    IGNORE_BUTTONS = ["ok_button"]

    helpLines = [
        "Make a selection using the arrow and enter keys, then "
    ]

    def create(self):
        super(WelcomeForm, self).create()

        self.sync_subject = self.add(
            FormSwitcher,
            scroll_exit=True,
            name="Sync Type",
            formOptions=OrderedDict( [
                    ( 'products', WooGenerator.PRODUCTS_FORM_ID),
                    ('customers', WooGenerator.CUSTOMERS_FORM_ID)
            ])
        )

    def on_cancel(self):
        logging.info("%s performing cancel", self.__class__)
        self.parentApp.setNextForm(None)
        self.parentApp.switchFormNow()

if __name__ == "__main__":
    logging.basicConfig(filename="woogenerator.log", level=logging.DEBUG)
    wgApp = WooGenerator()
    try:
        wgApp.run()
    except npyscreen.NotEnoughSpaceForWidget as e:
        print "not enough space for widget, try resizing terminal.", e

