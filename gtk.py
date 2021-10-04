#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import threading
from client import MailClient
from gi import require_version
from gi.repository import GObject, GLib

require_version( 'Gtk', '3.0' )

from gi.repository import Gtk

PER_PAGE = 10

lock = threading.BoundedSemaphore(1)


class MainWindow(Gtk.Window):

    # Tworzy wszystkie komponenty składające się na główne okno przeglądarki grafów.
    def __init__( self, mail_client ):
        super().__init__( title = "Outllok", window_position = Gtk.WindowPosition.CENTER )

        self.__mail_client = mail_client
        self.__page = 0
        main_layout = Gtk.Box( orientation = Gtk.Orientation.VERTICAL, homogeneous = False )

        # menu ---------------------------------------

        menu = Gtk.MenuBar()

        filemenu = Gtk.Menu()
        filem = Gtk.MenuItem("Pomoc")
        filem.set_submenu(filemenu)

        exit = Gtk.MenuItem("O programie")
        exit.connect("activate", self.__show_about_page)
        filemenu.append(exit)

        menu.append(filem)

        main_layout.pack_start(menu, False, False, 0)

        # header ---------------------------------
        header = Gtk.Box( orientation = Gtk.Orientation.HORIZONTAL, homogeneous = False )
        self.__create_button = Gtk.Button( label="Utwórz", image = Gtk.Image.new_from_icon_name( "document-new", Gtk.IconSize.BUTTON ) )
        self.__create_button.set_always_show_image (True)
        self.__create_button.set_sensitive(False)
        self.__create_button.connect("clicked", self.__show_create_mail_window)

        self.__spinner = Gtk.Spinner()

        self.__settings_button = Gtk.Button( label="Ustawienia", image = Gtk.Image.new_from_icon_name( "emblem-system", Gtk.IconSize.BUTTON ) )
        self.__settings_button.set_always_show_image (True)
        self.__settings_button.connect("clicked", self.__show_settings_window)

        header.pack_start(self.__create_button, False, False, 10)
        header.pack_start(self.__spinner, True, False, 0)
        header.pack_start(self.__settings_button, False, False, 10)
        main_layout.pack_start(header, False, False, 10)

        # main ---------------------------------------------------
        sw = Gtk.ScrolledWindow()

        self.__treeView = Gtk.TreeView()
        self.__treeView.connect("row-activated", self.on_activated)
        self.__treeView.set_rules_hint(True)

        rendererText = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Data", rendererText, text=0)
        column.set_fixed_width(250)
        column.set_sort_column_id(0)
        self.__treeView.append_column(column)

        rendererText = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Od", rendererText, text=1)
        column.set_sort_column_id(1)
        self.__treeView.append_column(column)

        rendererText = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Tytuł", rendererText, text=2)
        column.set_sort_column_id(2)
        self.__treeView.append_column(column)

        sw.add(self.__treeView)
        main_layout.pack_start(sw, True, True, 0)

        # footer -----------------------
        footer = Gtk.Box( orientation = Gtk.Orientation.HORIZONTAL, homogeneous = False )
        self.__next_button = Gtk.Button(image=Gtk.Image.new_from_icon_name("go-next", Gtk.IconSize.BUTTON))
        self.__next_button.set_sensitive(False)
        self.__next_button.connect("clicked", self.__show_next_page)
        self.__previous_button = Gtk.Button(image=Gtk.Image.new_from_icon_name("go-previous", Gtk.IconSize.BUTTON))
        self.__previous_button.set_sensitive(False)
        self.__previous_button.connect("clicked", self.__show_previous_page)
        self.__progress_label = Gtk.Label(label="1 / 1")

        footer.pack_start(self.__previous_button, False, True, 12)
        footer.pack_start(self.__progress_label, True, True, 0)
        footer.pack_start(self.__next_button, False, True, 12)

        main_layout.pack_start(footer, False, False, 10)

        self.add( main_layout )
        self.set_default_size( 1000, 600 )

        self.update()

    def reset_state(self):
        self.__spinner.stop()
        self.__treeView.set_model(Gtk.ListStore(str, str, str, str))
        self.__progress_label = Gtk.Label(label="1 / 1")
        self.__next_button.set_sensitive(False)
        self.__previous_button.set_sensitive(False)
        self.__create_button.set_sensitive(False)

    def __show_about_page(self, button):
        window = Gtk.Window(title="O programie", window_position=Gtk.WindowPosition.CENTER_ON_PARENT)
        window.set_transient_for(self)

        aboutText = open('./about.txt', 'r')

        textView = Gtk.TextView()
        textView.set_editable(False)
        buffer = Gtk.TextBuffer()
        buffer.set_text(aboutText.read())
        textView.set_buffer(buffer)

        window.add(textView)
        window.set_default_size(600, 400)
        window.show_all()

    def __show_previous_page(self, button):
        self.__page -= 1
        self.update(False)

    def __show_next_page(self, button):
        self.__page += 1
        self.update(False)

    def __update_async(self, loop):
        if self.__mail_client.is_connected():
            self.__spinner.start()
        self.__mail_client.get_messages_async(page=self.__page, per_page=PER_PAGE, obj=self,
                                              callback=self.__update_indicators)
        self.__previous_button.set_sensitive(False)
        self.__next_button.set_sensitive(False)
        if loop:
            GObject.timeout_add(5000, self.__update_async, [loop])


    def update(self, loop = True):
        print('update')
        self.__update_async(loop)

    def __update_indicators(self, messages):
        def update():
            self.__spinner.stop()
            lock.acquire()
            if messages is None:
                self.__treeView.set_model(Gtk.ListStore(str, str, str, str))
                lock.release()
                return

            self.__progress_label.set_label(str(self.__page + 1) + " / " + str(messages['totalPages']))
            if self.__page == 0:
                self.__previous_button.set_sensitive(False)
            else:
                self.__previous_button.set_sensitive(True)

            if self.__page == messages['totalPages'] - 1:
                self.__next_button.set_sensitive(False)
            else:
                self.__next_button.set_sensitive(True)

            def create_model():
                store = Gtk.ListStore(str, str, str, str)

                for msg in messages['data']:
                    store.append([msg['DATE2'], msg['FROM'], msg['SUBJECT'], msg['BODY_TEXT']])

                return store

            store = create_model()

            self.__treeView.set_model(store)
            lock.release()
        GObject.idle_add(update)

    def __show_settings_window(self, button):
        print("settings window")
        test_account = MailClient.get_test_account()
        window = Gtk.Window(title="Ustawienia", window_position=Gtk.WindowPosition.CENTER_ON_PARENT)
        window.set_transient_for(self)

        main = Gtk.VBox()

        header = Gtk.HBox()
        imap_label = Gtk.Label(label="Serwer IMAP:")
        imap_label.set_xalign(0)
        imap_label.set_size_request(100, -1)
        imap_text_box = Gtk.Entry()
        imap_text_box.set_text(test_account['imap'])
        header.pack_start(imap_label, False, True, 10)
        header.pack_start(imap_text_box, True, True, 10)
        main.pack_start(header, False, True, 10)

        header2 = Gtk.HBox()
        smtp_label = Gtk.Label(label="Serwer SMTP:")
        smtp_label.set_xalign(0)
        smtp_label.set_size_request(100, -1)
        smtp_text_box = Gtk.Entry()
        smtp_text_box.set_text(test_account['smtp'])
        header2.pack_start(smtp_label, False, True, 10)
        header2.pack_start(smtp_text_box, True, True, 10)
        main.pack_start(header2, False, True, 10)

        header3 = Gtk.HBox()
        login_label = Gtk.Label(label="Login:")
        login_label.set_size_request(100, -1)
        login_label.set_xalign(0)
        login_text_box = Gtk.Entry()  # get_text()
        login_text_box.set_text(test_account['login'])
        header3.pack_start(login_label, False, True, 10)
        header3.pack_start(login_text_box, True, True, 10)
        main.pack_start(header3, False, True, 10)

        header4 = Gtk.HBox()
        password_label = Gtk.Label(label="Hasło:")
        password_label.set_xalign(0)
        password_label.set_size_request(100, -1)
        password_text_box = Gtk.Entry()  # get_text()
        password_text_box.set_text(test_account['password'])
        password_text_box.set_visibility(False)
        header4.pack_start(password_label, False, True, 10)
        header4.pack_start(password_text_box, True, True, 10)
        main.pack_start(header4, False, True, 10)

        def update(button):
            self.__mail_client.set__credentials(imap_text_box.get_text(), smtp_text_box.get_text(), login_text_box.get_text(),
                                                password_text_box.get_text())
            try:
                self.__mail_client.connect()
                self.__create_button.set_sensitive(True)
                window.close()
                self.update(False)
            except Exception as ex:
                dialog = Gtk.MessageDialog(self, 0, Gtk.MessageType.ERROR,
                                           Gtk.ButtonsType.OK, "Error")
                dialog.format_secondary_text(str(ex))
                dialog.run()
                dialog.destroy()
                self.reset_state()

        send_button = Gtk.Button(label="Połącz", image=Gtk.Image.new_from_icon_name("view-refresh", Gtk.IconSize.BUTTON))
        send_button.set_always_show_image(True)
        send_button.connect("clicked", update)
        main.pack_start(send_button, False, False, 10)

        window.add(main)
        window.set_resizable(False)
        window.set_default_size(600, -1)
        window.show_all()

    def on_activated(self, widget, row, col):

        model = widget.get_model()

        window = Gtk.Window(title=model[row][2], window_position=Gtk.WindowPosition.CENTER_ON_PARENT)
        window.set_transient_for(self)

        main = Gtk.VBox()
        message_label = Gtk.Label(label="<b>Treść wiadomości</b>", use_markup=True)
        message = Gtk.TextView()
        scrolledPanel = Gtk.ScrolledWindow()
        scrolledPanel.add(message)
        message.set_editable(False)
        buffer = Gtk.TextBuffer()
        buffer.set_text(model[row][3])
        message.set_buffer(buffer)

        main.pack_start(message_label, False, True, 10)
        main.pack_start(scrolledPanel, True, True, 0)

        window.add(main)
        window.set_default_size(600, 400)

        window.show_all()


    def __show_create_mail_window(self, button):
        print("new mail window")
        window = Gtk.Window(title = "Nowa wiadomość", window_position = Gtk.WindowPosition.CENTER_ON_PARENT )
        window.set_transient_for(self)

        main = Gtk.VBox()

        header = Gtk.HBox()
        send_to_label = Gtk.Label(label = "Wyślij do:")
        send_to_label.set_size_request(100, -1)
        send_to_label.set_xalign(0)
        send_to_text_box = Gtk.Entry()
        header.pack_start(send_to_label, False, True, 10)
        header.pack_start(send_to_text_box, True, True, 10)
        main.pack_start(header, False, True, 10)

        header2 = Gtk.HBox()
        title_label = Gtk.Label(label = "Temat:")
        title_label.set_xalign(0)
        title_label.set_size_request(100, -1)
        title_text_box = Gtk.Entry()  #get_text()
        header2.pack_start(title_label, False, True, 10)
        header2.pack_start(title_text_box, True, True, 10)
        main.pack_start(header2, False, True, 10)

        mainBox = Gtk.VBox()
        message_label = Gtk.Label(label="<b>Treść wiadomości</b>", use_markup = True)
        message = Gtk.TextView()
        scrolledPanel = Gtk.ScrolledWindow()
        scrolledPanel.add(message)
        mainBox.pack_start(message_label, False, True, 10)
        mainBox.pack_start(scrolledPanel, True, True, 0)
        main.pack_start(mainBox, True, True, 0)


        def send_message(button):
            buffer = message.get_buffer()
            text = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), False)
            try:
                self.__mail_client.send_message(send_to_text_box.get_text(), title_text_box.get_text(), text)
                dialog = Gtk.MessageDialog(self, 0, Gtk.MessageType.INFO, Gtk.ButtonsType.OK, "Info")
                dialog.format_secondary_text("Pomyślnie wysłano wiadomość")
                dialog.run()
                dialog.destroy()
                window.close()
            except Exception as ex:
                dialog = Gtk.MessageDialog(self, 0, Gtk.MessageType.ERROR, Gtk.ButtonsType.OK, "Error")
                dialog.format_secondary_text(str(ex))
                dialog.run()
                dialog.destroy()

        send_button = Gtk.Button( label="Wyślij", image = Gtk.Image.new_from_icon_name( "mail-send", Gtk.IconSize.BUTTON ) )
        send_button.set_always_show_image (True)
        send_button.connect("clicked", send_message)
        main.pack_start(send_button, False, False, 0)

        window.add(main)
        window.set_default_size(600, 400)
        window.show_all()


client = MailClient()
view = MainWindow(client)
view.connect("delete-event", Gtk.main_quit)
view.show_all()
Gtk.main()

