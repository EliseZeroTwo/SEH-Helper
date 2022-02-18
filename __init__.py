from binaryninja import *
from binaryninjaui import WidgetPane, UIActionHandler, UIActionHandler, UIAction, Menu, UIContext, UIContextNotification
from pefile import ExceptionsDirEntryData, PE, PEFormatError
from PySide6 import QtCore
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QLabel, QWidget, QListWidget, QListWidgetItem, QTextEdit, QCheckBox, QPushButton
from PySide6.QtGui import QMouseEvent


class SEHListItem(QListWidgetItem):
    def __init__(self, base: int, entry: ExceptionsDirEntryData):
        self.entry = entry
        QListWidgetItem.__init__(self, hex(
            base + entry.struct.BeginAddress) + "-" + hex(base + entry.struct.EndAddress))


class AddrLabel(QLabel):
    def __init__(self, address, bv: BinaryView):
        self.bv = bv
        self.addr = address
        if self.addr != None:
            QLabel.__init__(self, hex(self.addr))
        else:
            QLabel.__init__(self, "")

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        button = event.button()
        modifiers = event.modifiers()
        if modifiers == Qt.NoModifier and button == Qt.LeftButton:
            if self.addr != None:
                self.bv.offset = self.addr
        return super().mouseReleaseEvent(event)

    def setAddr(self, addr):
        self.addr = addr
        if self.addr != None:
            self.setText(hex(self.addr))
        else:
            self.clear()


class SEHNotifications(UIContextNotification):
    def __init__(self, widget):
        UIContextNotification.__init__(self)
        self.widget = widget
        self.widget.destroyed.connect(self.destroyed)
        UIContext.registerNotification(self)

    def destroyed(self):
        UIContext.unregisterNotification(self)

    def OnAddressChange(self, context, frame, view, location):
        if self.widget.follow_cb.isChecked():
            self.widget.gotoAddr(location.getOffset())


class SEHWidget(QWidget, UIContextNotification):
    def gotoAddr(self, addr):
        for x in self.dict:
            if x[0] <= addr <= x[1]:
                row = self.dict[x]
                self.list.setCurrentRow(row)
                self.listItemClicked(self.list.item(row))
                return
        
        self.list.clearSelection()
        self.listItemClicked(None)

    def gotoButtonClicked(self):
        self.gotoAddr(self.bv.offset)

    def __init__(self, bv: BinaryView, file: PE):
        QWidget.__init__(self)
        layout = QVBoxLayout()

        header_layout = QHBoxLayout()

        self.follow_cb = QCheckBox()
        follow_layout = QHBoxLayout()
        follow_layout.addWidget(QLabel("Follow Cursor: "))
        follow_layout.addWidget(self.follow_cb)

        goto_button = QPushButton()
        goto_button.setText("Goto Cursor")
        goto_button.clicked.connect(self.gotoButtonClicked)

        header_layout.addWidget(goto_button)
        header_layout.addStretch()
        header_layout.addLayout(follow_layout)

        self.begin_addr = AddrLabel(None, bv)
        begin_addr_layout = QHBoxLayout()
        begin_addr_layout.addWidget(QLabel("Begin Address: "))
        begin_addr_layout.addWidget(self.begin_addr)

        self.end_addr = AddrLabel(None, bv)
        end_addr_layout = QHBoxLayout()
        end_addr_layout.addWidget(QLabel("End Address: "))
        end_addr_layout.addWidget(self.end_addr)

        self.unwind_addr = AddrLabel(None, bv)
        unwind_addr_layout = QHBoxLayout()
        unwind_addr_layout.addWidget(QLabel("Unwind Address: "))
        unwind_addr_layout.addWidget(self.unwind_addr)

        unwind_layout = QVBoxLayout()
        self.unwind_version = QLabel("")
        self.unwind_prolog_size = QLabel("")
        self.unwind_code_count = QLabel("")
        self.unwind_frame_register = QLabel("")
        self.unwind_frame_offset = QLabel("")
        self.unwind_flags = QLabel("")
        self.unwind_codes = QTextEdit()
        self.unwind_codes.setReadOnly(True)
        self.unwind_exception_handler = AddrLabel(None, bv)

        title = QLabel("Unwind Info")
        title.setAlignment(QtCore.Qt.AlignCenter)
        unwind_layout.addWidget(title)

        unwind_verison_layout = QHBoxLayout()
        unwind_verison_layout.addWidget(QLabel("Version: "))
        unwind_verison_layout.addWidget(self.unwind_version)
        unwind_layout.addLayout(unwind_verison_layout)

        unwind_flags_layout = QHBoxLayout()
        unwind_flags_layout.addWidget(QLabel("Flags: "))
        unwind_flags_layout.addWidget(self.unwind_flags)
        unwind_layout.addLayout(unwind_flags_layout)

        unwind_exception_handler_layout = QHBoxLayout()
        unwind_exception_handler_layout.addWidget(
            QLabel("Exception Handler: "))
        unwind_exception_handler_layout.addWidget(
            self.unwind_exception_handler)
        unwind_layout.addLayout(unwind_exception_handler_layout)

        unwind_prolog_size_layout = QHBoxLayout()
        unwind_prolog_size_layout.addWidget(QLabel("Prolog Size: "))
        unwind_prolog_size_layout.addWidget(self.unwind_prolog_size)
        unwind_layout.addLayout(unwind_prolog_size_layout)

        unwind_code_count_layout = QHBoxLayout()
        unwind_code_count_layout.addWidget(QLabel("Code Count: "))
        unwind_code_count_layout.addWidget(self.unwind_code_count)
        unwind_layout.addLayout(unwind_code_count_layout)

        unwind_frame_register_layout = QHBoxLayout()
        unwind_frame_register_layout.addWidget(QLabel("Frame Register: "))
        unwind_frame_register_layout.addWidget(self.unwind_frame_register)
        unwind_layout.addLayout(unwind_frame_register_layout)

        unwind_frame_offset_layout = QHBoxLayout()
        unwind_frame_offset_layout.addWidget(QLabel("Frame Offset: "))
        unwind_frame_offset_layout.addWidget(self.unwind_frame_offset)
        unwind_layout.addLayout(unwind_frame_offset_layout)

        unwind_codes_layout = QHBoxLayout()
        unwind_codes_layout.addWidget(QLabel("Codes: "))
        unwind_codes_layout.addWidget(self.unwind_codes)
        unwind_layout.addLayout(unwind_codes_layout)

        self.dict = {}
        self.list = QListWidget()
        self.list.currentItemChanged.connect(self.listItemClicked)
        ctr = 0
        for entry in file.DIRECTORY_ENTRY_EXCEPTION:
            item = SEHListItem(file.OPTIONAL_HEADER.ImageBase, entry)
            self.list.addItem(item)
            self.dict[(file.OPTIONAL_HEADER.ImageBase + entry.struct.BeginAddress,
                       file.OPTIONAL_HEADER.ImageBase + entry.struct.EndAddress)] = ctr
            ctr += 1

        list_layout = QHBoxLayout()
        list_layout.addWidget(QLabel("Entries: "))
        list_layout.addWidget(self.list)

        layout.addLayout(header_layout)
        layout.addLayout(list_layout)
        layout.addLayout(begin_addr_layout)
        layout.addLayout(end_addr_layout)
        layout.addLayout(unwind_addr_layout)
        layout.addLayout(unwind_layout)
        self.setLayout(layout)

        self.file = file
        self.bv = bv

        self.notifications = SEHNotifications(self)

    def listItemClicked(self, clickedItem):
        if clickedItem == None:
            self.begin_addr.setAddr(None)
            self.end_addr.setAddr(None)
            self.unwind_addr.setAddr(None)
            self.unwind_version.clear()
            self.unwind_flags.clear()
            self.unwind_prolog_size.clear()
            self.unwind_code_count.clear()
            self.unwind_frame_register.clear()
            self.unwind_frame_offset.clear()
            self.unwind_codes.clear()
            self.unwind_exception_handler.clear()
        else:
            self.begin_addr.setAddr(
                self.file.OPTIONAL_HEADER.ImageBase + clickedItem.entry.struct.BeginAddress)
            self.end_addr.setAddr(
                self.file.OPTIONAL_HEADER.ImageBase + clickedItem.entry.struct.EndAddress)
            self.unwind_addr.setAddr(
                self.file.OPTIONAL_HEADER.ImageBase + clickedItem.entry.struct.UnwindData)

            self.unwind_version.setText(str(clickedItem.entry.unwindinfo.Version))


            unwind_flags = []
            if clickedItem.entry.unwindinfo.Flags == 0:
                unwind_flags.append("UNW_FLAG_NHANDLER")
            if clickedItem.entry.unwindinfo.Flags & 1:
                unwind_flags.append("UNW_FLAG_EHANDLER")
            if clickedItem.entry.unwindinfo.Flags & 2:
                unwind_flags.append("UNW_FLAG_UHANDLER")
            if clickedItem.entry.unwindinfo.Flags & 4:
                unwind_flags.append("UNW_FLAG_CHAININFO")
            self.unwind_flags.setText(str(clickedItem.entry.unwindinfo.Flags) + " (" + (", ".join(unwind_flags)) + ")")

            self.unwind_prolog_size.setText(
                str(clickedItem.entry.unwindinfo.SizeOfProlog))
            self.unwind_code_count.setText(
                str(clickedItem.entry.unwindinfo.CountOfCodes))
            self.unwind_frame_register.setText(
                str(clickedItem.entry.unwindinfo.FrameRegister))
            self.unwind_frame_offset.setText(
                str(clickedItem.entry.unwindinfo.FrameOffset))
            codes = ""
            for x in clickedItem.entry.unwindinfo.UnwindCodes:
                codes += str(x) + '\n'
            self.unwind_codes.setText(codes)

            if hasattr(clickedItem.entry.unwindinfo, 'ExceptionHandler'):
                self.unwind_exception_handler.setAddr(
                    self.file.OPTIONAL_HEADER.ImageBase + clickedItem.entry.unwindinfo.ExceptionHandler)
            else:
                self.unwind_exception_handler.clear()

    @staticmethod
    def createPane(context):
        if context.context and context.binaryView and context.binaryView.parent_view:
            data = context.binaryView.parent_view.read(
                0, context.binaryView.parent_view.length)
            widget = SEHWidget(context.binaryView, PE(data=data))
            pane = WidgetPane(widget, "Structured Exception Handlers")
            context.context.openPane(pane)

    @staticmethod
    def canCreatePane(context):
        if context.context and context.binaryView and context.binaryView.parent_view:
            try:
                data = context.binaryView.parent_view.read(
                    0, context.binaryView.parent_view.length)
                PE(data=data, fast_load=True)
                return True
            except PEFormatError:
                return False
            except:
                raise
        return False


UIAction.registerAction("SEH Helper")
UIActionHandler.globalActions().bindAction(
    "SEH Helper", UIAction(SEHWidget.createPane, SEHWidget.canCreatePane)
)
Menu.mainMenu("Tools").addAction("SEH Helper", "SEH Helper")
