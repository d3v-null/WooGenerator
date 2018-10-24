# -*- coding: utf-8 -*-
"""Provides GUI for syncing products and customers."""
from __future__ import print_function

import contextlib
import logging
import platform
import sys
import traceback
import os
from collections import OrderedDict, namedtuple
from copy import deepcopy
from pprint import pformat

import npyscreen

from . import generator
from .utils import overrides
from .utils.core import SeqUtils

ScreenOffset = namedtuple('Offset', ['col', 'row'])
logging.basicConfig(filename="woogenerator.log", level=logging.DEBUG)


class WooGenerator(npyscreen.NPSAppManaged):
    """GUI Application for WooGenerator."""
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
            cycle_widgets=True)

        self.addForm(
            self.__class__.CUSTOMERS_FORM_ID, CustomersForm, name='Customers')

        self.addForm(
            self.__class__.CONFIRM_FORM_ID, ConfirmForm, name='Confirmation')

    @property
    def forms(self):
        """exposes the private forms dictionary."""
        return self._Forms

    @property
    def command_script(self):
        """
        Return the script selected by the user
        """
        confirm_form = self.getForm(self.__class__.CONFIRM_FORM_ID)
        if not confirm_form:
            return
        cmd_out_widget = confirm_form.command_script
        if not cmd_out_widget:
            return
        return cmd_out_widget.value

    @property
    def command_args(self):
        """
        Return the args specified by the user as displayed on config screen
        """
        confirm_form = self.getForm(self.__class__.CONFIRM_FORM_ID)
        if not confirm_form:
            return
        cmd_out_widget = confirm_form.command_args
        if not cmd_out_widget:
            return
        return cmd_out_widget.value


class SyncSelectOne(npyscreen.SelectOne):
    """Select Widget which tracks command particle info."""

    def __init__(self, *args, **kwargs):
        command_particles = kwargs.pop('cmd_particles', [])
        if command_particles:
            assert len(command_particles) == len(kwargs['values'])
        super(SyncSelectOne, self).__init__(*args, **kwargs)
        self.command_particles = command_particles

    @property
    def active_particle(self):
        """
        returns that active particle of this widget given the user selection
        """
        logging.debug("getting active particle. value: %s ", self.value)
        answer_index = self.value[0]
        if self.command_particles \
                and len(self.command_particles) > answer_index:
            return self.command_particles[answer_index]


class SyncTitleText(npyscreen.TitleText):
    """Text Widget which tracks command particle info."""

    def __init__(self, *args, **kwargs):
        command_particle = kwargs.pop('cmd_particle')
        super(SyncTitleText, self).__init__(*args, **kwargs)
        self.command_particle = command_particle

    @property
    def active_particle(self):
        """
        returns that active particle of this widget given the user selection
        """
        logging.debug("getting active particle. value: %s ", self.value)

        if self.value:
            return "%s '%s'" % (self.command_particle, self.value)


class SyncForm(npyscreen.ActionFormV2):  # pylint: disable=too-many-ancestors
    """Form used in by WooGenerator app."""
    BUTTON_META = OrderedDict([('ok_button', {
        'text': npyscreen.ActionFormV2.OK_BUTTON_TEXT,
        'type': npyscreen.ActionFormV2.OKBUTTON_TYPE,
    }),
                               ('cancel_button', {
                                   'text':
                                   npyscreen.ActionFormV2.CANCEL_BUTTON_TEXT,
                                   'type':
                                   npyscreen.ActionFormV2.CANCELBUTTON_TYPE
                               })])

    IGNORE_BUTTONS = []

    welcomeLines = []

    def __init__(self, *args, **kwargs):
        self.editw = None
        super(SyncForm, self).__init__(*args, **kwargs)
        self.command_particles = OrderedDict()

    @overrides(npyscreen.ActionFormV2)
    def create_control_buttons(self):
        current_b_offset = 1
        current_r_offset = 6
        for button_name, button_meta in self.__class__.BUTTON_META.items():
            logging.info("%s ignore buttons: %s", self.__class__,
                         self.__class__.IGNORE_BUTTONS)
            if button_name in self.__class__.IGNORE_BUTTONS:
                logging.info("%s ignoring button: %s", self.__class__,
                             button_name)
                continue
            button_text = button_meta.get('text', '')
            button_br_offset = ScreenOffset(
                0 - current_r_offset - len(button_text), 0 - current_b_offset)

            button_type = button_meta.get('type',
                                          self.__class__.CANCELBUTTON_TYPE)

            logging.info("%s creating button: %s", self.__class__, button_name)

            self._add_button(button_name, button_type, button_text,
                             button_br_offset.row, button_br_offset.col, None)

            current_r_offset += 4 + len(button_text)

    @property
    def widgets_by_id(self):
        """exposes the protected _widgets_by_id dict."""
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

    def add_single_line(self, line, **kwargs):
        """Add a single line of text as a npyscreen.Textfield widget."""
        field_kwargs = dict(editable=False, value=line)
        field_kwargs.update(**kwargs)
        self.add(npyscreen.Textfield, **field_kwargs)

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

        if help_str:
            self.add_paragraph([help_str], padding=0)

        widget_ref = self.add(
            SyncSelectOne,
            scroll_exit=True,
            max_height=len(kwargs['values']) + 1,
            **kwargs)

        logging.info("added widgetObj:\n%s\n%s", pformat((widget_ref)),
                     pformat((widget_ref.name)))

        for widget_id, widget_proxy in self.widgets_by_id.items():
            if widget_proxy == widget_ref:
                logging.info("found widget ID: %s", widget_id)

        return widget_ref

    def create(self):
        self.add_paragraph(self.welcomeLines)

    @property
    def active_particles(self):
        """
        returns an iterator of the active particles given the widget
        selections
        """
        for _, widget in self.widgets_by_id.items():
            if hasattr(widget, 'active_particle'):
                log_warning = "found compatible widget: %s, value: %s"
                log_args = [
                    widget.name,
                    widget.value,
                ]
                if hasattr(widget, 'command_particles'):
                    log_warning += ", particles:  %s"
                    log_args += [widget.command_particles]
                if hasattr(widget, 'command_particle'):
                    log_warning += ", particle:  %s"
                    log_args += [widget.command_particle]
                active_particle = widget.active_particle
                log_warning += ", active_particle: %s"
                log_args += [active_particle]
                logging.warning(log_warning, *log_args)
                if active_particle:
                    yield widget.active_particle


class ProductsForm(SyncForm):
    """A form for specifying product syncing parameters."""

    BUTTON_META = OrderedDict(SyncForm.BUTTON_META.items())
    BUTTON_META['ok_button']['text'] = 'Next'

    welcomeLines = [
        'Instructions: ', 'Use <Tab> to navigate to the next question',
        'Use <Control-C> to exit this program',
        (' - If you are uploading specials: tick '
         '"auto next special", "process categories", "process variations"'),
        ' - If you are uploading pricing changes: tick "no specials", "no variations"'
    ]

    @contextlib.contextmanager
    def increase_indent(self):
        """Context manager for increasing indent of widget."""
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
            value=1)

        # self.generate_report = self.add_simple_question(
        #     name="Generate Report",
        #     help_str="Would you like to generate a sync report? (slow)",
        #     cmd_particles=['--skip-report', '--do-report'],
        #     value=0
        # )

        self.process_specials = self.add_simple_question(
            name="Process Specials",
            help_str="How would you like to process specials?",
            values=[
                "No Specials",
                "Auto Next Special",
                "Override",
                # "All Future Specials"
            ],
            cmd_particles=[
                '--skip-specials',
                '--do-specials --specials-mode=auto_next',
                '--do-specials --specials-mode=override',
                # '--future-specials'
            ],
            value=0)

        with self.increase_indent():
            # indent process_specials questions
            self.specials_override = self.add(
                SyncTitleText,
                name="Specials Override",
                cmd_particle='--current-special',
                scroll_exit=True,
                hidden=True,
                value='')

        self.process_categories = self.add_simple_question(
            name="Process Categories",
            help_str="Would you like to process categories?",
            value=0,
            cmd_particles=['--skip-categories', '--do-categories'])

        with self.increase_indent():
            self.process_specials_categories = self.add_simple_question(
                name="Process Special Categories",
                help_str="Would you like to add special categories?",
                value=1,
                cmd_particles=['--skip-special-categories', ''])

        self.process_variations = self.add_simple_question(
            name="Process Variations",
            help_str="Would you like to process variations?",
            value=1,
            cmd_particles=['--skip-variations', '--do-variations'])

        self.process_images = self.add_simple_question(
            name="Process Images",
            help_str="Would you like to process images?",
            value=0,
            cmd_particles=['--skip-images', '--do-images'])

        self.auto_sync = self.add_simple_question(
            name="Auto Upload",
            help_str="Would you like to attempt to automatically sync?",
            value=0,
            cmd_particles=[
                '--skip-download-slave --skip-sync',
                '--download-slave --do-sync --auto-create-new'
            ])

        self.sync_dry_run = self.add_simple_question(
            name="Dry Run",
            help_str="Would you like preview the changes without making them?",
            value=0,
            cmd_particles=[
                ('--update-slave --auto-create-new --auto-delete-old '
                 '--do-problematic --ask-before-update'),
                ('--skip-update-slave --do-report --report-duplicates'
                 '--report-matching --do-mail --report-and-quit')
            ])

    @overrides(npyscreen.proto_fm_screen_area.ScreenArea)
    def refresh(self):
        super(ProductsForm, self).refresh()
        logging.debug("refreshing form")
        process_specials_widget = None
        specials_override_widget = None
        for _, widget in self.widgets_by_id.items():
            if widget.name == "Process Specials":
                process_specials_widget = widget
            if widget.name == "Specials Override":
                specials_override_widget = widget
        if not (process_specials_widget and specials_override_widget):
            return

        process_specials_value = process_specials_widget.value
        if isinstance(process_specials_value, list):
            process_specials_value = process_specials_value[0]
        specials_override_widget.hidden = \
            process_specials_widget.values[process_specials_value] != 'Override'

        logging.debug("value of process specials widget: %s",
                      process_specials_value)
        logging.debug("hidden of specials override widget: %s",
                      specials_override_widget.hidden)


class CustomersForm(SyncForm):
    """Form for specifying customer sync parameters."""
    welcomeLines = ["CUSTOMERS"]

    # def create(self):
    # super(CustomersForm, self).create()


class ConfirmForm(SyncForm):
    """Form for confirming sync parameters."""
    BUTTON_META = deepcopy(SyncForm.BUTTON_META)
    BUTTON_META['ok_button']['text'] = 'Go!'

    def create(self):
        self.command_script = self.add(
            npyscreen.TitleFixedText, name="Script", value="")
        self.command_args = self.add(
            npyscreen.TitleFixedText, name="Arguments", value="")

    @overrides(npyscreen.fm_form_edit_loop.FormNewEditLoop)
    def pre_edit_loop(self):  # pylint: disable=invalid-name,missing-docstring
        welcome_form = self.parentApp.getForm('MAIN')
        if welcome_form:
            command_particles = []
            # command_particles.append('python')
            active_form_id = welcome_form.sync_subject.active_form_id
            active_form = self.parentApp.getForm(active_form_id)
            logging.info("active form widgets: ")
            for widget in active_form.widgets_by_id:
                if hasattr(widget, "name"):
                    logging.info("name: %20s | %s", widget.name, widget)
                else:
                    logging.info("no name: %s", widget)
            if not active_form:
                self.command_script.value = "no active form"
                return
            elif active_form_id == 'PRODUCTS':
                self.command_script.value = 'woogenerator.generator'
            # elif active_form_id == 'CUSTOMERS':
            #     self.command_script.value = 'merger.py'
            else:
                self.command_script.value = "unknown active_form_id"
                return
            new_active_particles = active_form.active_particles
            if new_active_particles:
                command_particles.extend(list(new_active_particles))
            self.command_args.value = ' '.join(command_particles)

    def on_ok(self):
        logging.info("performing ok")
        self.parentApp.setNextForm(None)


class FormSwitcher(npyscreen.MultiLineAction):
    """Widget that selects which form to go to next."""

    def __init__(self, *args, **kwargs):
        self.form_options = kwargs.pop('form_options', OrderedDict)
        kwargs.update(values=self.form_options.keys())
        # pylint: disable=invalid-name
        self._activeFormName = kwargs.get('value')
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
        """Returns the form name selected by the user."""
        return self.form_options.get(self._activeFormName)

    @property
    def active_form(self):
        """Returns a reference to the form selected by the user."""
        return self.parent.parentApp.getForm(self.active_form_id)


class WelcomeForm(SyncForm):
    """Main form used by WooGenerator app where user selects the sync type."""
    if platform.system() != 'Darwin':
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
            ' '.join([tanLine, syncLine])
            for tanLine, syncLine in zip(tanLines, syncLines)
        ]
    welcomeLines += [
        "", "Welcome to the TanSync Utility.", "",
        "What would you like to sync?", ""
    ]

    # logging.debug("welcomeLines: %s", welcomeLines)

    IGNORE_BUTTONS = ["ok_button"]

    helpLines = ["Make a selection using the arrow and enter keys, then "]

    def create(self):
        super(WelcomeForm, self).create()

        self.sync_subject = self.add(
            FormSwitcher,
            scroll_exit=True,
            name="Sync Type",
            form_options=OrderedDict(
                [('products', WooGenerator.PRODUCTS_FORM_ID),
                 ('customers', WooGenerator.CUSTOMERS_FORM_ID)]))

    def on_cancel(self):
        logging.info("%s performing cancel", self.__class__)
        self.parentApp.setNextForm(None)
        self.parentApp.switchFormNow()


def main():
    """Main method for gui."""

    wg_app = WooGenerator()
    try:
        wg_app.run(fork=False)
    except npyscreen.NotEnoughSpaceForWidget as exc:
        print("not enough space for widget, try resizing terminal.", exc)
        traceback.print_exception(*sys.exc_info())

    # fix terminal freezes after running for a few seconds until traceback
    sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)

    override_args = SeqUtils.filter_unique_true(sys.argv[1:] +
                                                wg_app.command_args.split())
    print("cmd out value: %s <- %s" % (
        wg_app.command_script, " ".join(override_args)))
    if wg_app.command_script == 'woogenerator.generator':
        generator.catch_main(override_args=override_args)


if __name__ == "__main__":
    logging.debug("\n\nEntering main!")
    main()
