""" Provides GUI for syncing products and customers """
# -*- coding: utf-8 -*-
import os
import logging
# from pprint import pprint
from pprint import pformat
import contextlib
from collections import namedtuple, OrderedDict
from utils import overrides
# import weakref

import npyscreen
# from npyscreen import NPSAppManaged
# from npyscreen import Form, AProductsFormctionForm
# from npyscreen import TitleText, TitleSelectOne, MultiLine, MultiLineEdit

ScreenOffset = namedtuple('Offset', ['col', 'row'])

class WooGenerator(npyscreen.NPSAppManaged):
    """ GUI Application for WooGenerator """
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

class SyncSelectOne(npyscreen.SelectOne):
    """ Widget which tracks command particle info """

class SyncForm(npyscreen.ActionFormV2): # pylint: disable=too-many-ancestors
    """ Form used in by WooGenerator app """
    BUTTON_META = OrderedDict([
        (
            'ok_button', {
                'text':npyscreen.ActionFormV2.OK_BUTTON_TEXT,
                'type':npyscreen.ActionFormV2.OKBUTTON_TYPE,
            }
        ),
        (
            'cancel_button', {
                'text':npyscreen.ActionFormV2.CANCEL_BUTTON_TEXT,
                'type':npyscreen.ActionFormV2.CANCELBUTTON_TYPE
            }
        )
    ])

    IGNORE_BUTTONS = []

    def __init__(self, *args, **kwargs):
        self.editw = None
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

    @property
    def widgets_by_id(self):
        """ exposes the protected _widgets_by_id dict """
        return self._widgets_by_id

    def find_cancel_button(self):
        assert 'cancel_button' in self.__class__.BUTTON_META
        button_index = self.__class__.BUTTON_META.keys().index('cancel_button')
        self.editw = len(self._widgets__) - 2 - button_index

    def on_cancel(self):
        logging.info("performing cancel")
        self.parentApp.switchFormPrevious()

    def on_ok(self):
        logging.info("performing ok")
        self.parentApp.switchForm(WooGenerator.CONFIRM_FORM_ID)

    welcomeLines = [
    ]

    def add_single_line(self, line, **kwargs):
        """ Add a single line of text as a npyscreen.Textfield widget """
        field_kwargs = dict(
            editable=False,
            value=line
        )
        field_kwargs.update(**kwargs)
        self.add(
            npyscreen.Textfield,
            **field_kwargs
        )

    def add_paragraph(self, lines, **kwargs):
        """ adds a list of lines as npyscreen.Textfield widgets with optional
        padding parameter """
        padding = kwargs.pop('padding', 1)
        if lines:
            if lines[-1] and padding:
                for _ in range(padding):
                    lines.append('')
            for line in lines:
                self.add_single_line(line, **kwargs)

    def add_simple_question(self, help_str=None, **kwargs):
        """
        Add a simple question widget (SyncWidget).

        Arguments:
            help_str (str):
                Question asked to user
            values (list[str]):
                Answers to chose from
                Default: ["No", "Yes"]
            value (int):
                index of default answer
                Default: 1
            name (str):
                Name of widget
            command_particles (list[str]):
                list of particles that are generated for each answer

        Return:
            :class:`weakref`: reference to widget created
        """

        if 'values' not in kwargs:
            kwargs['values'] = ["No", "Yes"]
        if 'value' not in kwargs:
            kwargs['value'] = 1
        if 'name' not in kwargs:
            kwargs['name'] = ''
        if kwargs['command_particles']:
            # self.command_particles[name] =
            pass

        if help_str:
            self.add_paragraph(
                [help_str],
                padding=0
            )

        widget_ref = self.add(
            SyncSelectOne,
            scroll_exit=True,
            max_height=len(kwargs['values']) + 1
            **kwargs
        )

        logging.info(
            "added widgetObj:\n%s\n%s",
            pformat((widget_ref)),
            pformat((widget_ref.name))
        )

        for widget_id, widget_proxy in self.widgets_by_id.items():
            if widget_proxy == widget_ref:
                logging.info("found widget ID: %s", widget_id)


        return widget_ref

    def create(self):
        self.add_paragraph(self.welcomeLines)

    @property
    def active_particles(self):
        """ returns the active particles given the widget selections """
        # TODO: Complete this
        # for widget_id, widget in self.widgets_by_id:
        pass


class ProductsForm(SyncForm):
    """ A form for specifying product syncing parameters """

    BUTTON_META = SyncForm.BUTTON_META
    BUTTON_META['ok_button']['text'] = 'Next'

    @contextlib.contextmanager
    def increase_indent(self):
        """ Context manager for increasing indent of widget """
        self.current_indent += 1
        yield
        self.current_indent -= 1

    def create(self):
        self.current_indent = 0

        super(ProductsForm, self).create()

        self.download_master = self.add_simple_question(
            name="Download Master",
            help_str="Has the Google Drive Spreadsheet Been updated recently?",
            cmd_particles=['--skip-download-master', '--download-master'],
            value=1
        )

        self.generate_report = self.add_simple_question(
            name="Generate Report",
            help_str="Would you like to generate a sync report? (slow)",
            cmd_particles=['--skip-report', '--show-report'],
            value=0
        )

        self.process_specials = self.add_simple_question(
            name="Process Specials",
            help_str="How would you like to process specials?",
            values=[
                "No Specials",
                "Auto Next Special",
                # "All Future Specials"
            ],
            cmd_particles=[
                '--skip-specials',
                '--specials-mode=\'auto_next\'',
                # '--future-specials'
            ],
            value=0
        )

        # with self.increase_indent():
        #     # indent process_specials questions
        #     self.add_paragraph(
        #         ["What is the specials override?"],
        #         hidden=True
        #     )
        #     self.specials_override = self.add(
        #         npyscreen.Textfield,
        #         name="Specials Override",
        #         scroll_exit=True,
        #         hidden=True
        #     )

        self.process_categories = self.add_simple_question(
            name="Process Categories",
            help_str="Would you like to process categories?",
            value=0,
            cmd_particles=['--skip-categories', '--do-categories']
        )

        self.process_variations = self.add_simple_question(
            name="Process Variations",
            help_str="Would you like to process variations?",
            value=0,
            cmd_particles=['--skip-variations', '--do-variations']
        )

class CustomersForm(SyncForm):
    """ Form for specifying customer sync parameters """
    welcomeLines = [
        "CUSTOMERS"
    ]


    def create(self):
        super(CustomersForm, self).create()

class ConfirmForm(SyncForm):
    """ Form for confirming sync parameters """
    def create(self):
        self.command_out = self.add(
            npyscreen.TitleFixedText,
            name="Command",
            value="cmd:"
        )

    @overrides(npyscreen.Form)
    def beforeEditing(self): # pylint: disable=invalid-name,missing-docstring
        welcome_form = self.parentApp.getForm('MAIN')
        if welcome_form:
            command_particles = ['python']
            active_form_id = welcome_form.sync_subject.active_form_id
            active_form = self.parentApp.getForm(active_form_id)
            logging.info("active form widgets: ")
            for widget in active_form.widgets_by_id:
                if hasattr(widget, "name"):
                    logging.info("name: %20s | %s", widget.name, widget)
                else:
                    logging.info("no name: %s", pformat(dir(widget)))
            if not active_form:
                self.command_out.value = "no active form"
                return
            elif active_form_id == 'PRODUCTS':
                command_particles.append('source/generator.py')
            elif active_form_id == 'CUSTOMERS':
                command_particles.append('source/merger.py')
            else:
                self.command_out.value = "unknown active_form_id"
                return
            new_active_particles = active_form.active_particles
            if new_active_particles:
                command_particles.extend(new_active_particles)
            self.command_out.value = ' '.join(command_particles)

class FormSwitcher(npyscreen.MultiLineAction):
    """ Widget that selects which form to go to next """
    def __init__(self, *args, **kwargs):
        self.form_options = kwargs.pop('form_options', OrderedDict)
        kwargs.update(
            values=self.form_options.keys()
        )
        self._activeFormName = kwargs.get('value') # pylint: disable=invalid-name
        super(FormSwitcher, self).__init__(*args, **kwargs)

    def actionHighlighted(self, act_on_this, key_press):
        super(FormSwitcher, self).actionHighlighted(act_on_this, key_press)
        self._activeFormName = act_on_this
        logging.info("actionHighlighted: %s %s", act_on_this, key_press)
        next_form = self.form_options.get(act_on_this)
        logging.info("setting next form to %s", next_form)
        self.parent.parentApp.setNextForm(next_form)
        self.parent.parentApp.switchFormNow()

    @property
    def active_form_id(self):
        """ Returns the form name selected by the user """
        return self.form_options.get(self._activeFormName)

    @property
    def active_form(self):
        """ Returns a reference to the form selected by the user """
        return self.parent.parentApp.getForm(self.active_form_id)


class WelcomeForm(SyncForm):
    """ Main form used by WooGenerator app where user selects the sync type """
    if os.name == 'nt':
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
        welcomeLines = [
            ' '.join([tanLine, syncLine]) \
                for tanLine in tanLines \
                for syncLine in syncLines
        ]
    welcomeLines += [
        "",
        "Welcome to the TanSync Utility.",
        "",
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
            form_options=OrderedDict([
                ('products', WooGenerator.PRODUCTS_FORM_ID),
                ('customers', WooGenerator.CUSTOMERS_FORM_ID)
            ])
        )

    def on_cancel(self):
        logging.info("%s performing cancel", self.__class__)
        self.parentApp.setNextForm(None)
        self.parentApp.switchFormNow()

def main():
    """ Main method for gui """
    logging.basicConfig(filename="woogenerator.log", level=logging.DEBUG)
    logging.debug("NEW START\n\n")
    wg_app = WooGenerator()
    try:
        wg_app.run()
    except npyscreen.NotEnoughSpaceForWidget as exc:
        print "not enough space for widget, try resizing terminal.", exc

if __name__ == "__main__":
    main()
