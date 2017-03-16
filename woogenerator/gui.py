# -*- coding: utf-8 -*-
import os
import logging
from pprint import pprint, pformat
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
            name="Products",
            cycle_widgets=True
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

    def __init__(self, *args, **kwargs):
        super(SyncForm, self).__init__(*args, **kwargs)
        self.command_particles = OrderedDict()

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

    def on_ok(self):
        logging.info("performing ok")
        self.parentApp.switchForm(WooGenerator.CONFIRM_FORM_ID)

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
                          answers=None, indent=1, cmd_particles=None):

        if answers is None:
            answers=["No", "Yes"]

        if not name:
            name=""

        if cmd_particles:
            # self.command_particles[name] =
            pass

        if help_str:
            self.addParagraph(
                [ help_str ],
                padding=0
            )

        if default is None:
            default=1

        widgetObj = self.add(
            npyscreen.SelectOne,
            scroll_exit=True,
            name=name,
            values=answers,
            value=default,
            max_height=len(answers) + 1
        )

        logging.info("added widgetObj:\n%s\n%s", pformat( widgetObj ),
                     pformat((widgetObj.name)))

        return widgetObj

    def create(self):
        self.addParagraph(self.welcomeLines)

    @property
    def activeParticles(self):
        #todo: complete this
        pass

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
            cmd_particles=['--skip-download-master', '--download-master'],
            default=1
        )

        self.generate_report = self.addSimpleQuestion(
            name="Generate Report",
            help_str="Would you like to generate a sync report? (slow)",
            cmd_particles=['--skip-report', '--show-report'],
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
            cmd_particles=[
                '--skip-specials',
                '--latest-special',
                '--future-specials'
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
            default=0,
            cmd_particles=['--skip-categories', '--do-categories']
        )

        self.process_variations = self.addSimpleQuestion(
            name="Process Variations",
            help_str="Would you like to process variations?",
            default=0,
            cmd_particles=['--skip-variations','--do-variations']
        )

class CustomersForm(SyncForm):
    welcomeLines = [
        "CUSTOMERS"
    ]


    def create(self):
        super(CustomersForm, self).create()

class ConfirmForm(SyncForm):
    def create(self):
        self.command_out = self.add(
            npyscreen.TitleFixedText,
            name="Command",
            value="cmd:"
        )

    def beforeEditing(self):
        welcomeForm = self.parentApp.getForm('MAIN')
        if welcomeForm:
            command_particles = ['python']
            activeFormID = welcomeForm.sync_subject.activeFormID
            activeForm = self.parentApp.getForm(activeFormID)
            logging.info("active form widgets: ")
            for widget in activeForm._widgets_by_id:
                if hasattr(widget, "name"):
                    logging.info("name: %20s | %s", widget.name, widget)
                else:
                    logging.info("no name: %s", pformat(dir(widget)))
            if not activeForm:
                self.command_out.value = "no active form"
                return
            elif activeFormID == 'PRODUCTS':
                command_particles.append('source/generator.py')
            elif activeFormID == 'CUSTOMERS':
                command_particles.append('source/merger.py')
            else:
                self.command_out.value = "unknown activeFormID"
                return
            newActiveParticles = activeForm.activeParticles
            if newActiveParticles:
                command_particles.extend(newActiveParticles)
            self.command_out.value =' '.join(command_particles)

class FormSwitcher(npyscreen.MultiLineAction):
    def __init__(self, *args, **kwargs):
        self.formOptions = kwargs.pop('formOptions', OrderedDict)
        kwargs.update(
            values=self.formOptions.keys()
        )
        self._activeFormName = kwargs.get('value')
        super(FormSwitcher, self).__init__(*args, **kwargs)

    def actionHighlighted(self, act_on_this, key_press):
        super(FormSwitcher, self).actionHighlighted(act_on_this, key_press)
        self._activeFormName = act_on_this
        logging.info("actionHighlighted: %s %s", act_on_this, key_press)
        next_form = self.formOptions.get(act_on_this)
        logging.info("setting next form to %s" , next_form)
        self.parent.parentApp.setNextForm(next_form)
        self.parent.parentApp.switchFormNow()

    @property
    def activeFormID(self):
        return self.formOptions.get(self._activeFormName)

    @property
    def activeForm(self):
        return self.parent.parentApp.getForm(self.activeFormID)


class WelcomeForm(SyncForm):
    if os.name != 'nt':
        welcomeLines = [
            r" _______ _______ __   _ _______ __   __ __   _ _______",
            r"    |    |_____| | \  | |______   \_/   | \  | |      ",
            r"    |    |     | |  \_| ______|    |    |  \_| |_____ ",
        ]
    else:
        tanLines = [
            " ██████████████                                  ",
            " ██          ██ ██████████████ ███████   ██████ ",
            " ██████  ██████ ██          ██ ██    █  ██  ██ ",
            "     ██  ██     ██  ██████  ██ ██    █ ██  ██ ",
            "     ██  ██     ██  ██  ██  ██ ██  █  ███  ██ ",
            "     ██  ██     ██  ██████  ██ ██  ██  ███  ██ ",
            "     ██  ██     ██          ██ ██  ███  ██  ██ ",
            "     ██  ██     ██  ██████  ██ ██  ███  █  ██ ",
            "     ██  ██     ██  ██  ██  ██ ██  ██ █    ██ ",
            "     ██  ██     ██  ██  ██  ██ ██  ██  █    ██ ",
            "     ██  ██     ██  ██  ██  ██ ██  ██   █   ██ ",
            "     ██████     ██████  ██████ ██████    ██████ ",
        ]
        syncLines = [
            "██████████████",
            "██          ██ ██████  ██████ ███████   ██████ ██████████████ ",
            "██  ██████████ █  ██  █ ██    █  ██  ██ ██          ██ ",
            "██  ██          █  ██  █  ██    █ ██  ██ ██  ██████████ ",
            "██  ██████████   █    █   ██  █  ███  ██ ██  ██         ",
            "██          ██    █    █    ██  ██  ███  ██ ██  ██         ",
            "██████████  ██     █  █     ██  ███  ██  ██ ██  ██         ",
            "        ██  ██      ██  ██      ██  ███  █  ██ ██  ██         ",
            "        ██  ██      ██  ██      ██  ██ █    ██ ██  ██         ",
            "██████████  ██      ██  ██      ██  ██  █    ██ ██  ██████████ ",
            "██          ██      ██  ██      ██  ██   █   ██ ██          ██ ",
            "██████████████      ██████      ██████    ██████ ██████████████ ",
        ]
        welcomeLines = map(
            (lambda *args: ' '.join(args)),
            tanLines,
            syncLines
        )
    welcomeLines += [
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
