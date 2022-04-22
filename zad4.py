import csv, sys, re
import xml.etree.ElementTree as xml
from typing import Union
from datetime import datetime
from xml.dom import minidom
from dotenv import dotenv_values
import _mysql_connector
import mysql.connector as conn

from PyQt5 import QtWidgets as qt
from PyQt5 import QtCore as qtc
from PyQt5 import QtGui as qtg

class ItemDelegate(qt.QItemDelegate):
    def __init__(self, parent, regex: qtc.QRegExp):
        super(ItemDelegate, self).__init__(parent)
        self.regex = regex

    def createEditor(self, parent: qt.QWidget, option: 'qt.QStyleOptionViewItem', index: qtc.QModelIndex) -> qt.QWidget:
        line = qt.QLineEdit(parent)
        validator = qtg.QRegExpValidator(self.regex, parent)
        line.setValidator(validator)
        return line


class IntegerItemDelegate(qt.QStyledItemDelegate):
    def __init__(self, parent, imin: int, imax: int, suffix: Union[str, None]): #str | None
        super(IntegerItemDelegate, self).__init__(parent)
        self.min = imin
        self.max = imax
        self.suffix = suffix

    def createEditor(self, parent: qt.QWidget, option: 'qt.QStyleOptionViewItem', index: qtc.QModelIndex) -> qt.QWidget:
        spin_box = qt.QSpinBox(parent)
        spin_box.setMinimum(self.min)
        spin_box.setMaximum(self.max)
        return spin_box

    def displayText(self, text, locale):
        if self.suffix:
            return qt.QStyledItemDelegate.displayText(self, text, locale) + self.suffix
        else:
            return qt.QStyledItemDelegate.displayText(self, text, locale)


class ComboItemDelegate(qt.QItemDelegate):
    def __init__(self, parent, values):
        super(ComboItemDelegate, self).__init__(parent)
        self.values = values

    def createEditor(self, parent: qt.QWidget, option: 'qt.QStyleOptionViewItem', index: qtc.QModelIndex) -> qt.QWidget:
        combo_box = qt.QComboBox(parent)
        combo_box.addItems(self.values)
        return combo_box


def noner(item: qt.QTableWidgetItem, suffix: Union[str, None] = None):
    if item.text() == "---" or item.text() == "":
        return None
    elif suffix is not None:
        return item.text() + suffix
    elif item.text() == "tak":
        return "yes"
    elif item.text() == "nie":
        return "no"
    else:
        return item.text()


def noner_db(item: qt.QTableWidgetItem):
    if item.text() == "---" or item.text() == "":
        return "NULL"
    elif re.search("([0-9]+x[0-9]+)", item.text()):
        return item.text().split('x')
    elif item.text() == "tak":
        return '1'
    elif item.text() == "nie":
        return '0'
    else:
        return item.text()


def rower_db(table: qt.QTableWidget, row: int) -> str:
    init = "INSERT INTO `laptop` (`manufacturer`, `screen_size`, `screen_width`, `screen_height`, `matrix_type`, `is_touch`, `cpu`, `cpu_cores`, `cpu_clock`, `ram`, `disk_space`, `disk_type`, `gpu`, `gpu_mem`, `os`, `odd`) VALUES ("
    end = ')'
    body = ''
    for column in range(table.columnCount()):
        if column == 2:
            resolution = noner_db(table.item(row, column))
            if resolution[0] == "N":
                resolution = "NULL, NULL"
            else:
                resolution = resolution[0] + ", " + resolution[1]
            body = body + resolution + ", "
        elif noner_db(table.item(row, column)) == 'NULL':
            body = body + noner_db(table.item(row, column)) + ", "
        else:
            body = body + "'" + noner_db(table.item(row, column)) + "', "
    body = body[:-2]
    return init+body+end


class App(qt.QWidget):
    names = ['Producent', 'Przekątna', 'Rozdzielczość', 'Typ ekranu', 'Dotykowy ekran', 'CPU', 'Rdzenie', 'Taktowanie [MHz]', 'Ilość RAM', 'Pojemność dysku', 'Rodzaj dysku', 'GPU', 'Pamięć GPU', 'OS', 'Napęd ODD']

    def __init__(self, parent=None):
        super(App, self).__init__(parent)
        self.db = None
        self.credentials = dotenv_values()

        # Creating Qt window
        self.temp = None
        self.setWindowTitle("Integracja systemów zad. 4 - Karol Buchajczuk")
        layout = qt.QVBoxLayout()

        # Creating layout for buttons
        self.button_group_box = qt.QGroupBox("Opcje")
        self.db_group_box = qt.QGroupBox("Baza danych")
        button_layout = qt.QHBoxLayout()
        db_layout = qt.QHBoxLayout()

        # Adding buttons to window
        self.import_txt = qt.QPushButton("Import z .txt")
        self.export_txt = qt.QPushButton("Export do .txt")
        self.import_xml = qt.QPushButton("Import z .xml")
        self.export_xml = qt.QPushButton("Export do .xml")
        self.add_row = qt.QPushButton("Dodaj wiersz")
        self.del_row = qt.QPushButton("Usuń wiersz")

        self.import_txt.clicked.connect(self.import_from_txt)
        self.export_txt.clicked.connect(self.export_to_txt)
        self.import_xml.clicked.connect(self.import_from_xml)
        self.export_xml.clicked.connect(self.export_to_xml)
        self.add_row.clicked.connect(lambda: self.table.insertRow(self.table.rowCount()))
        self.del_row.clicked.connect(self.delete_row)

        self.import_txt.setMaximumWidth(300)
        self.export_txt.setMaximumWidth(300)
        self.import_xml.setMaximumWidth(300)
        self.export_xml.setMaximumWidth(300)
        self.add_row.setMaximumWidth(300)
        self.del_row.setMaximumWidth(300)

        self.connect_db = qt.QPushButton("Połącz z bazą danych")
        self.import_db = qt.QPushButton("Import z bazy")
        self.export_db = qt.QPushButton("Export do bazy")

        self.connect_db.clicked.connect(self.connect_to_db)
        self.import_db.clicked.connect(self.import_from_db)
        self.export_db.clicked.connect(self.export_to_db)

        self.connect_db.setMaximumWidth(300)
        self.import_db.setMaximumWidth(300)
        self.import_db.setEnabled(False)
        self.export_db.setMaximumWidth(300)
        self.export_db.setEnabled(False)

        self.db_status_box = qt.QGroupBox("Status połączenia")
        db_status_layout = qt.QHBoxLayout()
        self.db_status = qt.QLabel("Brak połączenia")
        db_status_layout.addWidget(self.db_status)
        self.db_status_box.setLayout(db_status_layout)
        self.db_status_box.setMaximumWidth(300)

        # Setting column names
        self.table = qt.QTableWidget()
        self.table.setColumnCount(len(self.names))
        self.table.setHorizontalHeaderLabels(self.names)

        # Setting validators
        self.table.setItemDelegateForColumn(1, IntegerItemDelegate(self, 0, 150, '"'))
        self.table.setItemDelegateForColumn(3, ComboItemDelegate(self, ["matowa", "blyszczaca", "---"]))
        self.table.setItemDelegateForColumn(4, ComboItemDelegate(self, ["tak", "nie"]))
        self.table.setItemDelegateForColumn(6, IntegerItemDelegate(self, 0, 24, None))
        self.table.setItemDelegateForColumn(7, IntegerItemDelegate(self, 0, 9999, None))
        self.table.setItemDelegateForColumn(8, IntegerItemDelegate(self, 0, 1024, "GB"))
        self.table.setItemDelegateForColumn(9, IntegerItemDelegate(self, 0, 1024, "GB"))
        self.table.setItemDelegateForColumn(10, ComboItemDelegate(self, ["SSD", "HDD", "---"]))
        self.table.setItemDelegateForColumn(12, IntegerItemDelegate(self, 0, 1024, "GB"))
        self.table.setItemDelegateForColumn(14, ComboItemDelegate(self, ["Blu-Ray", "DVD", "brak", "---"]))

        self.table.itemChanged.connect(self.validate)
        self.table.itemDoubleClicked.connect(self.save_val)

        # Setting layouts and executing app
        button_layout.addWidget(self.import_txt)
        button_layout.addWidget(self.export_txt)
        button_layout.addWidget(self.import_xml)
        button_layout.addWidget(self.export_xml)
        button_layout.addWidget(self.add_row)
        button_layout.addWidget(self.del_row)

        db_layout.addWidget(self.connect_db)
        db_layout.addWidget(self.db_status_box)
        db_layout.addWidget(self.import_db)
        db_layout.addWidget(self.export_db)

        self.button_group_box.setLayout(button_layout)
        self.db_group_box.setLayout(db_layout)
        layout.addWidget(self.button_group_box)
        layout.addWidget(self.db_group_box)
        layout.addWidget(self.table)

        self.counter = qt.QLabel()
        layout.addWidget(self.counter)
        self.setLayout(layout)

    def import_from_txt(self):
        try:
            file_dialog = qt.QFileDialog(self)
            file_dialog.setWindowTitle('Open file')
            file_dialog.setNameFilter('(*.csv *.txt)')
            file_dialog.setDirectory('~')
            file_dialog.setFileMode(qt.QFileDialog.ExistingFile)
            filename = None
            if file_dialog.exec_() == qt.QDialog.Accepted:
                filename = file_dialog.selectedFiles()
            if filename:
                self.table.setRowCount(0)
                with open(filename[0], newline='') as csvfile:
                    csvreader = csv.reader(csvfile, delimiter=";")
                    for number, item in enumerate(csvreader):
                        self.table.insertRow(self.table.rowCount())
                        item.pop()
                        for value in range(len(item)):
                            if item[value] == '':
                                self.table.setItem(number, value, qt.QTableWidgetItem('---'))
                            else:
                                self.table.setItem(number, value, qt.QTableWidgetItem(re.sub('"|(GB)', '', item[value])))
        except (TypeError, IndexError, FileNotFoundError):
            self.table.setRowCount(0)
            alert = qt.QMessageBox()
            alert.setText("Nie można otworzyć pliku!")
            alert.exec_()
        self.counter.setText("Rekordów: " + str(self.table.rowCount()))

    def export_to_txt(self):
        for row in range(self.table.rowCount()):
            for column in range(self.table.columnCount()):
                if self.table.item(row, column) is None:
                    alert = qt.QMessageBox()
                    alert.setText("Niektóre pola są puste!")
                    alert.exec_()
                    return None
        if self.table.item(0, 0) is None:
            alert = qt.QMessageBox()
            alert.setText("Brak danych do zapisania!")
            alert.exec_()
        else:
            file_dialog = qt.QFileDialog.getSaveFileName(self, "Save File", "", 'Text file(*.txt)')
            if file_dialog:
                if not re.match(r".+\.txt", file_dialog[0]):
                    filename = file_dialog[0] + ".txt"
                else:
                    filename = file_dialog[0]
                with open(filename, 'w') as stdout:
                    writer = csv.writer(stdout, delimiter=";")
                    for row in range(self.table.rowCount()):
                        rowdata = []
                        for column in range(self.table.columnCount()):
                            item = self.table.item(row, column)
                            if item is None:
                                rowdata.append('')
                            elif item.text() == "" or item.text() == "---":
                                rowdata.append('')
                            elif column == 1:
                                rowdata.append(item.text() + '"')
                            elif column in (8, 9, 12):
                                rowdata.append(item.text() + 'GB')
                            else:
                                rowdata.append(item.text())
                        rowdata.append('')
                        writer.writerow(rowdata)

    def import_from_xml(self):
        try:
            file_dialog = qt.QFileDialog(self)
            file_dialog.setWindowTitle('Open file')
            file_dialog.setNameFilter('(*.xml)')
            file_dialog.setDirectory('~')
            file_dialog.setFileMode(qt.QFileDialog.ExistingFile)
            filename = None
            if file_dialog.exec_() == qt.QDialog.Accepted:
                filename = file_dialog.selectedFiles()
            if filename:
                self.table.setRowCount(0)
                tree = xml.parse(filename[0])
                xml_root = tree.getroot()
                for number, child in enumerate(xml_root):
                    item = []
                    self.table.insertRow(self.table.rowCount())
                    item.append(child.find('manufacturer').text)
                    item.append(child.find('screen').find('size').text)
                    item.append(child.find('screen').find('resolution').text)
                    item.append(child.find('screen').find('type').text)
                    item.append(child.find('screen').get('touch'))
                    item.append(child.find('processor').find('name').text)
                    item.append(child.find('processor').find('physical_cores').text)
                    item.append(child.find('processor').find('clock_speed').text)
                    item.append(child.find('ram').text)
                    item.append(child.find('disc').find('storage').text)
                    item.append(child.find('disc').get('type'))
                    item.append(child.find('graphic_card').find('name').text)
                    item.append(child.find('graphic_card').find('memory').text)
                    item.append(child.find('os').text)
                    item.append(child.find('disc_reader').text)
                    for value in range(len(item)):
                        if item[value] == '' or item[value] is None:
                            self.table.setItem(number, value, qt.QTableWidgetItem('---'))
                        elif item[value] == 'yes':
                            self.table.setItem(number, value, (qt.QTableWidgetItem('tak')))
                        elif item[value] == 'no':
                            self.table.setItem(number, value, (qt.QTableWidgetItem('nie')))
                        else:
                            self.table.setItem(number, value, qt.QTableWidgetItem(re.sub('"|(GB)', '', item[value])))
        except (TypeError, IndexError, FileNotFoundError, xml.ParseError):
            self.table.setRowCount(0)
            alert = qt.QMessageBox()
            alert.setText("Nie można otworzyć pliku!")
            alert.exec_()
        self.counter.setText("Rekordów: " + str(self.table.rowCount()))

    def export_to_xml(self):
        for row in range(self.table.rowCount()):
            for column in range(self.table.columnCount()):
                if self.table.item(row, column) is None:
                    alert = qt.QMessageBox()
                    alert.setText("Niektóre pola są puste!")
                    alert.exec_()
                    return None
        if self.table.item(0, 0) is None:
            alert = qt.QMessageBox()
            alert.setText("Brak danych do zapisania!")
            alert.exec_()
        else:
            file_dialog = qt.QFileDialog.getSaveFileName(self, "Save File", "", 'XML file(*.xml)')
            if file_dialog:
                if not re.match(r".+\.xml", file_dialog[0]):
                    filename = file_dialog[0] + ".xml"
                else:
                    filename = file_dialog[0]
                with open(filename, 'w') as stdout:
                    root = xml.Element('laptops', {'moddate': datetime.now().strftime("%Y-%m-%d T %H:%M")})
                    for row in range(self.table.rowCount()):
                        laptop = xml.SubElement(root, 'laptop', {'id': str(row+1)})
                        xml.SubElement(laptop, "manufacturer").text = noner(self.table.item(row, 0))

                        screen = xml.SubElement(laptop, "screen", {"touch": noner(self.table.item(row, 4))})
                        xml.SubElement(screen, "size").text = noner(self.table.item(row, 1), '"')
                        xml.SubElement(screen, "resolution").text = noner(self.table.item(row, 2))
                        xml.SubElement(screen, "type").text = noner(self.table.item(row, 3))

                        processor = xml.SubElement(laptop, "processor")
                        xml.SubElement(processor, "name").text = noner(self.table.item(row, 5))
                        xml.SubElement(processor, "physical_cores").text = noner(self.table.item(row, 6))
                        xml.SubElement(processor, "clock_speed").text = noner(self.table.item(row, 7))

                        xml.SubElement(laptop, "ram").text = noner(self.table.item(row, 8), "GB")
                        disc = xml.SubElement(laptop, "disc", {"type": str(noner(self.table.item(row, 10)))})
                        xml.SubElement(disc, "storage").text = noner(self.table.item(row, 9), "GB")

                        gpu = xml.SubElement(laptop, "graphic_card")
                        xml.SubElement(gpu, "name").text = noner(self.table.item(row, 11))
                        xml.SubElement(gpu, "memory").text = noner(self.table.item(row, 12), "GB")

                        xml.SubElement(laptop, "os").text = noner(self.table.item(row, 13))
                        xml.SubElement(laptop, "disc_reader").text = noner(self.table.item(row, 14))
                    xml_string = minidom.parseString(xml.tostring(root)).toprettyxml(indent="")
                    stdout.write(xml_string)

    def connect_to_db(self):
        try:
            self.db = conn.connect(host=self.credentials.get("DB_HOST"),
                                   user=self.credentials.get("DB_USER"),
                                   password=self.credentials.get("DB_PASSWORD"),
                                   database=self.credentials.get("DB_DATABASE"))
            self.db.autocommit = True
            self.db_status.setText("Połączono")
            self.db_status.setStyleSheet("QLabel { color : green }")
            self.import_db.setEnabled(True)
            self.export_db.setEnabled(True)
        except (_mysql_connector.MySQLInterfaceError, conn.errors.DatabaseError):
            self.db_status.setText("Nie udało się połączyć do bazy danych")
            self.db_status.setStyleSheet("QLabel { color : red }")
            self.import_db.setEnabled(False)
            self.export_db.setEnabled(False)

    def import_from_db(self):
        self.table.setRowCount(0)
        cursor = self.db.cursor()
        cursor.execute("SELECT * from `laptop`")
        data = cursor.fetchall()
        for number, item in enumerate(data):
            self.table.insertRow(self.table.rowCount())
            item_data = list(item)
            item_data.pop(0)

            if item_data[2] is None:
                item_data.pop(2)
            else:
                item_data[2] = str(item_data[2]) + "x" + str(item_data[3])
                item_data.pop(3)

            item_data[4] = "tak" if item_data[4] == 1 else "nie"

            for value in range(len(item_data)):
                if item_data[value] is None:
                    self.table.setItem(number, value, qt.QTableWidgetItem('---'))
                else:
                    self.table.setItem(number, value, qt.QTableWidgetItem(str(item_data[value])))
        self.counter.setText("Rekordów: " + str(self.table.rowCount()))

    def export_to_db(self):
        for row in range(self.table.rowCount()):
            for column in range(self.table.columnCount()):
                if self.table.item(row, column) is None:
                    alert = qt.QMessageBox()
                    alert.setText("Niektóre pola są puste!")
                    alert.exec_()
                    return None
        if self.table.item(0, 0) is None:
            alert = qt.QMessageBox()
            alert.setText("Brak danych do zapisania!")
            alert.exec_()
        else:
            cursor = self.db.cursor()
            for row in range(self.table.rowCount()):
                cursor.execute(rower_db(self.table, row))
            alert = qt.QMessageBox()
            alert.setText("Zapisano do bazy")
            alert.exec_()

    def validate(self, item):
        row, column = item.row(), item.column()
        if self.table.item(row, column).text() == "":
            self.table.setItem(row, column, qt.QTableWidgetItem("---"))
        if column == 2:
            if not re.search("([0-9]+x[0-9]+)|(---)", self.table.item(row, column).text()):
                alert = qt.QMessageBox()
                alert.setText("Niepoprawny format")
                alert.exec_()
                self.table.setItem(row, column, qt.QTableWidgetItem(self.temp))
        if column in (1, 6, 7, 8, 9, 12):
            if self.table.item(row, column).text() == "" or self.table.item(row, column).text() == "0":
                self.table.setItem(row, column, qt.QTableWidgetItem("---"))

    def save_val(self, item):
        row, column = item.row(), item.column()
        self.temp = self.table.item(row, column).text()

    def delete_row(self):
        if self.table.rowCount() < 1:
            alert = qt.QMessageBox()
            alert.setText("Brak wierszy do usunięcia")
            alert.exec_()
        else:
            dialog = qt.QDialog()
            delete_layout = qt.QVBoxLayout()
            label = qt.QLabel("Wybierz wiersz do usunięcia")
            delete_layout.addWidget(label)

            row_select_spin = qt.QSpinBox()
            row_select_spin.setMinimum(1)
            row_select_spin.setMaximum(self.table.rowCount())
            delete_layout.addWidget(row_select_spin)

            delete_button = qt.QPushButton("Usuń wiersz")
            delete_button.clicked.connect(lambda: self.table.removeRow(row_select_spin.value()-1))
            delete_layout.addWidget(delete_button)

            dialog.setLayout(delete_layout)
            dialog.exec_()


app = qt.QApplication(sys.argv)
ui = App()
ui.show()
sys.exit(app.exec_())
