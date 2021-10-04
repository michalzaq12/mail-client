#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import threading

from PyQt5 import QtWidgets, QtGui, QtCore
from client import MailClient
from sys import argv

PER_PAGE = 10

lock = threading.RLock()


class GraphViewer( QtWidgets.QDialog ):

    def __init__( self, mail_client ):
        super().__init__( flags = QtCore.Qt.Window )
        self.__page = 0
        self.setWindowTitle( "Outllok" )

        self.__mail_client = mail_client

        main_layout = QtWidgets.QVBoxLayout()

        # menu ---------------------------------------------------------------------

        mainMenu = QtWidgets.QMenuBar()
        fileMenu = mainMenu.addMenu('&Pomoc')

        about = QtWidgets.QAction("&O programie", self)
        about.triggered.connect(self.__show_about_page)
        fileMenu.addAction(about)

        main_layout.addWidget(mainMenu)

        # header --------------------------------------------------------------------
        header = QtWidgets.QHBoxLayout()

        self.__create_button = QtWidgets.QPushButton(
            QtWidgets.QApplication.instance().style().standardIcon( QtWidgets.QStyle.SP_FileIcon ), "  Utwórz"
        )
        self.__create_button.clicked.connect(self.__show_create_mail_window)
        self.__create_button.setEnabled(False)

        self.__spinner = QtWidgets.QProgressBar()
        self.__spinner.setRange(0, 2)
        self.__spinner.setValue(0)
        self.__spinner.setEnabled(False)


        self.__settings_button = QtWidgets.QPushButton(
            QtWidgets.QApplication.instance().style().standardIcon( QtWidgets.QStyle.SP_FileDialogDetailedView), " Ustawienia"
        )
        self.__settings_button.clicked.connect(self.__show_settings_window)

        header.addWidget(self.__create_button, 0, QtCore.Qt.AlignLeft)
        header.addWidget(self.__spinner, 1, QtCore.Qt.AlignCenter)
        header.addWidget(self.__settings_button, 0, QtCore.Qt.AlignRight)

        # main ---------------------------------------------------------------------
        self.__list_view = QtWidgets.QTreeWidget()

        self.__list_view.setColumnCount(4)
        self.__list_view.setColumnHidden(3, True)
        self.__list_view.setHeaderLabels(["Data", "Od", "Temat"])
        self.__list_view.setColumnWidth(0, 250)
        self.__list_view.setColumnWidth(1, 300)


        self.__list_view.doubleClicked.connect(self.__on_activated)

        # footer ----------------------------------------------------------------------

        footer = QtWidgets.QHBoxLayout()
        self.__next_button = QtWidgets.QPushButton(
            QtWidgets.QApplication.instance().style().standardIcon(QtWidgets.QStyle.SP_ArrowRight), ""
        )
        self.__next_button.setEnabled(False)
        self.__previous_button = QtWidgets.QPushButton(
            QtWidgets.QApplication.instance().style().standardIcon(QtWidgets.QStyle.SP_ArrowLeft), ""
        )
        self.__previous_button.setEnabled(False)
        self.__progress_label = QtWidgets.QLabel("1 / 1")

        self.__previous_button.clicked.connect(self.__show_previous_page)
        self.__next_button.clicked.connect(self.__show_next_page)

        footer.addWidget(self.__previous_button)
        footer.addWidget(self.__progress_label, 1, QtCore.Qt.AlignCenter)
        footer.addWidget(self.__next_button)

        main_layout.addLayout(header)
        main_layout.addWidget(self.__list_view)
        main_layout.addLayout(footer)
        self.setLayout( main_layout )
        self.update()

    # Domyślny rozmiar okna.
    def sizeHint( self ):
        return QtCore.QSize( 1000, 600 )

    def reset_state(self):
        self.__spinner.setValue(0)
        self.__progress_label = QtWidgets.QLabel("1 / 1")

        items_to_remove = []
        root = self.__list_view.invisibleRootItem()
        iterator = QtWidgets.QTreeWidgetItemIterator(self.__list_view)
        while iterator.value():
            item = iterator.value()
            items_to_remove.append(item)
            iterator += 1

        for item in items_to_remove:
            root.removeChild(item)

        self.__next_button.setEnabled(False)
        self.__previous_button.setEnabled(False)
        self.__create_button.setEnabled(False)

    def __show_about_page(self, button):
        window = QtWidgets.QDialog(parent=self)
        window.setWindowTitle("O programie")
        main = QtWidgets.QVBoxLayout()

        aboutText = open('./about.txt', 'r')

        message_view = QtWidgets.QPlainTextEdit()
        message_view.insertPlainText(aboutText.read())
        message_view.setReadOnly(True)

        main.addWidget(message_view)

        window.setLayout(main)

        window.setFixedSize(600, 400)

        window.show()


    def __show_previous_page(self):
        self.__page -= 1
        self.update(False)

    def __show_next_page(self):
        self.__page += 1
        self.update(False)

    def __update_async(self):
        if self.__mail_client.is_connected():
            self.__spinner.setValue(2)
        self.__mail_client.get_messages_async(page=self.__page, per_page=PER_PAGE, obj=self, callback = self.__update_indicators)
        self.__previous_button.setEnabled(False)
        self.__next_button.setEnabled(False)

    def __update_indicators(self, messages):
        print("update indicator")
        self.__spinner.setValue(0)
        if messages is None:
            return

        self.__progress_label.setText(str(self.__page + 1) + " / " + str(messages['totalPages']))
        print(self.__page)
        if self.__page == 0:
            self.__previous_button.setEnabled(False)
        else:
            self.__previous_button.setEnabled(True)

        if self.__page == messages['totalPages'] - 1:
            self.__next_button.setEnabled(False)
        else:
            self.__next_button.setEnabled(True)

        def create_model():
            for msg in messages['data']:
                item = QtWidgets.QTreeWidgetItem()
                item.setText(0, msg['DATE2'])
                item.setText(1, msg['FROM'])
                item.setText(2, msg['SUBJECT'])
                item.setText(3, msg['BODY_TEXT'])
                self.__list_view.addTopLevelItem(item)

        root = self.__list_view.invisibleRootItem()
        items_to_remove = []

        iterator = QtWidgets.QTreeWidgetItemIterator(self.__list_view)
        while iterator.value():
            item = iterator.value()
            items_to_remove.append(item)
            iterator += 1

        for item in items_to_remove:
            root.removeChild(item)

        create_model()


    def update(self, loop = True):
        print('update')
        self.__update_async()
        if loop:
            QtCore.QTimer().singleShot(5000, self.update)


    def __on_activated(self, item):
        itemRow = item.row()
        contentIndex = item.model().index(itemRow, 3)
        content = item.model().data(contentIndex)
        titleIndex = item.model().index(itemRow, 2)
        title = item.model().data(titleIndex)

        window = QtWidgets.QDialog(parent=self)
        window.setWindowTitle(title)

        main = QtWidgets.QVBoxLayout()
        message_label = QtWidgets.QLabel(text="<b>Treść wiadomości</b>")
        message_view = QtWidgets.QPlainTextEdit()
        message_view.insertPlainText(content)
        message_view.setReadOnly(True)

        main.addWidget(message_label, 0, QtCore.Qt.AlignCenter)
        main.addWidget(message_view)

        window.setLayout(main)
        window.setFixedSize(600, 400)
        window.show()

    def __show_create_mail_window(self):
        print("new mail window")
        window = QtWidgets.QDialog(parent=self)
        window.setWindowTitle("Nowa wiadomość")

        main = QtWidgets.QVBoxLayout()

        header = QtWidgets.QHBoxLayout()
        send_to_label = QtWidgets.QLabel(text = "Wyślij do:")
        send_to_label.setFixedSize(100, 50)
        send_to_text_box = QtWidgets.QLineEdit()
        header.addWidget(send_to_label)
        header.addWidget(send_to_text_box)
        main.addLayout(header)

        header2 = QtWidgets.QHBoxLayout()
        subject_label = QtWidgets.QLabel(text="Temat:")
        subject_label.setFixedSize(100, 50)
        subject_text_box = QtWidgets.QLineEdit()
        header2.addWidget(subject_label)
        header2.addWidget(subject_text_box)
        main.addLayout(header2)

        message_panel = QtWidgets.QVBoxLayout()
        message_label = QtWidgets.QLabel(text="<b>Treść wiadomości</b>")
        message_view = QtWidgets.QPlainTextEdit()
        message_panel.addWidget(message_label, 0, QtCore.Qt.AlignCenter)
        message_panel.addWidget(message_view)
        main.addLayout(message_panel, 1)

        def send_message():
            try:
                self.__mail_client.send_message(send_to_text_box.text(), subject_text_box.text(), message_view.toPlainText())
                info = QtWidgets.QMessageBox()
                info.information(self, "Info", "Pomyślnie wysłano wiadomość")
                window.close()
            except Exception as ex:
                error_box = QtWidgets.QMessageBox(self)
                error_box.critical(self, "Error", str(ex))

        send_button = QtWidgets.QPushButton(
            QtWidgets.QApplication.instance().style().standardIcon(QtWidgets.QStyle.SP_DialogYesButton), "Wyślij"
        )
        send_button.clicked.connect(send_message)
        main.addWidget(send_button)

        window.setLayout(main)
        window.setFixedSize(600, 400)
        window.show()



    def __show_settings_window(self):
        print("settings window")
        test_account = MailClient.get_test_account()
        window = QtWidgets.QDialog(parent=self)
        window.setWindowTitle("Ustawienia")

        main = QtWidgets.QVBoxLayout()

        header = QtWidgets.QHBoxLayout()
        imap_label = QtWidgets.QLabel(text="Serwer IMAP:")
        imap_label.setFixedSize(150, 50)
        imap_text_box = QtWidgets.QLineEdit()
        imap_text_box.setText(test_account['imap'])

        header.addWidget(imap_label, 0)
        header.addWidget(imap_text_box, 0)
        main.addLayout(header)

        header2 = QtWidgets.QHBoxLayout()
        smtp_label = QtWidgets.QLabel(text="Serwer SMTP:")
        smtp_label.setFixedSize(150, 50)
        smtp_text_box = QtWidgets.QLineEdit()
        smtp_text_box.setText(test_account['smtp'])

        header2.addWidget(smtp_label, 0)
        header2.addWidget(smtp_text_box, 0)
        main.addLayout(header2)

        header3 = QtWidgets.QHBoxLayout()
        login_label = QtWidgets.QLabel(text="Login:")
        login_label.setFixedSize(150, 50)
        login_text_box = QtWidgets.QLineEdit()
        login_text_box.setText(test_account['login'])

        header3.addWidget(login_label, 0)
        header3.addWidget(login_text_box, 0)
        main.addLayout(header3)

        header4 = QtWidgets.QHBoxLayout()
        password_label = QtWidgets.QLabel(text="Hasło:")
        password_label.setFixedSize(150, 50)
        password_text_box = QtWidgets.QLineEdit()
        password_text_box.setEchoMode(QtWidgets.QLineEdit.Password)
        password_text_box.setText(test_account['password'])

        header4.addWidget(password_label, 0)
        header4.addWidget(password_text_box, 0)
        main.addLayout(header4)

        def update():
            self.__mail_client.set__credentials(imap_text_box.text(), smtp_text_box.text(), login_text_box.text(), password_text_box.text())
            try:
                self.__mail_client.connect()
                self.__create_button.setEnabled(True)
                window.close()
                self.update(False)
            except Exception as ex:
                error_box = QtWidgets.QMessageBox(self)
                error_box.critical(self, "Error", str(ex))
                self.reset_state()


        send_button = QtWidgets.QPushButton(
            QtWidgets.QApplication.instance().style().standardIcon(QtWidgets.QStyle.SP_BrowserReload), "Połącz"
        )
        send_button.clicked.connect(update)
        main.addWidget(send_button)

        window.setLayout(main)

        window.setFixedSize(600, 300)
        window.show()


# Główna część programu.
client = MailClient()
a = QtWidgets.QApplication( argv )
t = QtCore.QTranslator()
t.load( "qt_" + QtCore.QLocale.system().name(), QtCore.QLibraryInfo.location( QtCore.QLibraryInfo.TranslationsPath ) )
a.installTranslator( t )
w = GraphViewer( client )
w.show()
a.exec_()

