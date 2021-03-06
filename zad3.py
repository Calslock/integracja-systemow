import csv, sys, re
import xml.etree.ElementTree as xml
from typing import Union
from datetime import datetime
from xml.dom import minidom


from PyQt5 import QtWidgets as qt
from PyQt5 import QtCore as qtc
from PyQt5 import QtGui as qtg

# python>=3.6


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
        if suffix is None:
            return None
        elif suffix == "disc":
            return ""
    elif suffix == "disc":
        return item.text()
    elif suffix is not None:
        return item.text() + suffix
    elif item.text() == "tak":
        return "yes"
    elif item.text() == "nie":
        return "no"
    else:
        return item.text()


class App(qt.QWidget):
    names = ['Producent', 'Przek??tna', 'Rozdzielczo????', 'Typ ekranu', 'Dotykowy ekran', 'CPU', 'Rdzenie', 'Taktowanie [MHz]', 'Ilo???? RAM', 'Pojemno???? dysku', 'Rodzaj dysku', 'GPU', 'Pami???? GPU', 'OS', 'Nap??d ODD']

    def __init__(self, parent=None):
        super(App, self).__init__(parent)

        # Creating Qt window
        self.temp = None
        self.setWindowTitle("Integracja system??w zad. 3 - Karol Buchajczuk")
        layout = qt.QVBoxLayout()

        # Creating layout for buttons
        self.button_group_box = qt.QGroupBox("Opcje")
        button_layout = qt.QHBoxLayout()

        # Adding buttons to window
        self.import_txt = qt.QPushButton("Import z .txt")
        self.export_txt = qt.QPushButton("Export do .txt")
        self.import_xml = qt.QPushButton("Import z .xml")
        self.export_xml = qt.QPushButton("Export do .xml")
        self.add_row = qt.QPushButton("Dodaj wiersz")
        self.del_row = qt.QPushButton("Usu?? wiersz")

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

        self.button_group_box.setLayout(button_layout)
        layout.addWidget(self.button_group_box)
        layout.addWidget(self.table)
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
                    # Adding content
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
            alert.setText("Nie mo??na otworzy?? pliku!")
            alert.exec_()

    def export_to_txt(self):
        for row in range(self.table.rowCount()):
            for column in range(self.table.columnCount()):
                if self.table.item(row, column) is None:
                    alert = qt.QMessageBox()
                    alert.setText("Niekt??re pola s?? puste!")
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
                            #else:
                                #match column:
                                    #case 1:
                                        #rowdata.append(item.text() + '"')
                                    #case 8 | 9 | 12:
                                        #rowdata.append(item.text() + 'GB')
                                    #case _:
                                        #rowdata.append(item.text())
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
            alert.setText("Nie mo??na otworzy?? pliku!")
            alert.exec_()

    def export_to_xml(self):
        for row in range(self.table.rowCount()):
            for column in range(self.table.columnCount()):
                if self.table.item(row, column) is None:
                    alert = qt.QMessageBox()
                    alert.setText("Niekt??re pola s?? puste!")
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
                        manufacturer = xml.SubElement(laptop, "manufacturer").text = noner(self.table.item(row, 0))

                        screen = xml.SubElement(laptop, "screen", {"touch": noner(self.table.item(row, 4))})
                        size = xml.SubElement(screen, "size").text = noner(self.table.item(row, 1), '"')
                        resolution = xml.SubElement(screen, "resolution").text = noner(self.table.item(row, 2))
                        type = xml.SubElement(screen, "type").text = noner(self.table.item(row, 3))

                        processor = xml.SubElement(laptop, "processor")
                        cname = xml.SubElement(processor, "name").text = noner(self.table.item(row, 5))
                        cores = xml.SubElement(processor, "physical_cores").text = noner(self.table.item(row, 6))
                        clock = xml.SubElement(processor, "clock_speed").text = noner(self.table.item(row, 7))

                        ram = xml.SubElement(laptop, "ram").text = noner(self.table.item(row, 8), "GB")
                        disc = xml.SubElement(laptop, "disc", {"type": str(noner(self.table.item(row, 10), "disc"))})
                        storage = xml.SubElement(disc, "storage").text = noner(self.table.item(row, 9), "GB")

                        gpu = xml.SubElement(laptop, "graphic_card")
                        gname = xml.SubElement(gpu, "name").text = noner(self.table.item(row, 11))
                        memory = xml.SubElement(gpu, "memory").text = noner(self.table.item(row, 12), "GB")

                        os = xml.SubElement(laptop, "os").text = noner(self.table.item(row, 13))
                        odd = xml.SubElement(laptop, "disc_reader").text = noner(self.table.item(row, 14))
                    xml_string = minidom.parseString(xml.tostring(root)).toprettyxml(indent="")
                    stdout.write(xml_string)

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
            alert.setText("Brak wierszy do usuni??cia")
            alert.exec_()
        else:
            dialog = qt.QDialog()
            delete_layout = qt.QVBoxLayout()
            label = qt.QLabel("Wybierz wiersz do usuni??cia")
            delete_layout.addWidget(label)

            row_select_spin = qt.QSpinBox()
            row_select_spin.setMinimum(1)
            row_select_spin.setMaximum(self.table.rowCount())
            delete_layout.addWidget(row_select_spin)

            delete_button = qt.QPushButton("Usu?? wiersz")
            delete_button.clicked.connect(lambda: self.table.removeRow(row_select_spin.value()-1))
            delete_layout.addWidget(delete_button)

            dialog.setLayout(delete_layout)
            dialog.exec_()


app = qt.QApplication(sys.argv)
ui = App()
ui.show()
sys.exit(app.exec_())
