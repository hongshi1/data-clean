Open Watcom Linux Port GUI Software Requirements Specification

Copyright © 2004 SciTech Software, Inc.

<table><tr><td>Open Watcom Linux Port</td><td>Page 2 of 54</td></tr><tr><td>GUI Software Requirements Specification</td><td></td></tr></table>

## Table of Contents

Executive Summary 7   
1. Introduction 7   
1.1 About this document 7   
1.2 Document structure 7   
2. GTK Overview 8   
3. General GUI Porting Approach 8   
4. Issues 12   
5. Target System Requirements 13   
Detailed Porting Guidelines and Estimation 14   
Initial Stage 14   
6. GUI Library Initialization. 14   
GUIXMain 14   
SetupClass 15   
\_wpi\_postquitmessage 15   
GUILoadStrInit 15   
GUIWinMessageLoop 15   
Summary 15   
7. Display window initialization 16   
GUIWndInit 16   
\_wpi\_setdouibleclicktime 16   
GUIInitDialogFunc 16   
\_wpi\_enddialog 16   
Summary 17   
8. Window creation 17   
GUIXCreateWindow 19   
GUICalcLocation 19   
\_wpi\_createsolidbrush 20   
\_wpi\_create\_window\_ex 20   
\_wpi\_setredraw 20   
GUIMaximizeWindow 20   
GUIMinimizeWindow 20   
\_wpi\_showwindow 20   
GUIShowWindowNA 20   
GUIFreeWindowMemory 20   
Summary 21   
9. Standard sample 22   
GUIXCreateDialog 27   
SciTech Software, Inc.   
Open Watcom Linux Port Page 3 of 54   
GUI Software Requirements Specification   
GUIDoCreateResDialog 28   
DialogTemplate 28   
AddControl 28   
DoneAddingControls 28   
DynamicDialogBox 28   
GUIDialogFunc 28   
GUIDestroyWnd 28   
GUIGetText 28   
GUISendMessage 29   
GUIWndDirty 29   
GUIGetMetrics 29   
GUIGetClientRect 29   
\_wpi\_mapwindowpoints 29   
\_wpi\_getwrectvalues 30   
\_wpi\_getheightrect 30   
DrawRect 30   
GUIXDrawText 30   
Summary 30   
Elaboration stage 30   
10. Common control functions 30   
GUIAddControl 31   
GUIResizeControl 31   
\_wpi\_destroywindow 31   
GUIEnableControl 31   
\_wpi\_enablewindow 31   
GUIIsControlEnabled 31   
\_wpi\_iswindowenabled 32   
GUIGetControlRect 32   
\_wpi\_showwindow 32   
\_wpi\_iswindowwisible 32   
Summary 32   
11. Common text functions 32   
GUISetText 32   
GUIClearText 33   
GUISelectAll 33   
GUISetEditSelect 33   
GUIGetEditSelect 33   
GUIDlgBuffGetText 33   
Summary 33   
12. Special dialogs functions 34   
GUIDisplayMessage 34   
DlgOpen 34   
GUIGetDlgTextMetrics 34   
GUIGetSystemMetrics 35   
DlgSetCtlSizes 35   
GUIGetEditSelect 35   
GUIDlgBuffGetText 35   
Summary 35   
Open Watcom Linux Port Page 4 of 54   
GUI Software Requirements Specification   
13. Scrolling functions 35   
Common guidelines 36   
Summary 36   
14. Status window functions 36   
Common guidelines 36   
GUICreateStatusWindow 37   
GUICloseStatusWindow 37   
GUIDrawStatusText 37   
GUIResizeStatusWindow 37   
Summary 37   
15. Toolbar functions 37   
Common guidelines 37   
GUICreateFloatToolBar 37   
GUICreateToolBar 37   
GUICloseToolBar 38   
GUIChangeToolBar 38   
Summary 38   
16. Menu functions 38   
Common guidelines 38   
GUIAppendMenu 38   
GUIAppendMenuByOffset 39   
GUIInsertMenu 39   
GUIEnableMenuItem 39   
GUIEnableMenuItem 39   
GUISetMenuText 39   
GUISetHintText 39   
GUIDeleteMenuItem 40   
GUIResetMenus 40   
GUIEnableMDIMenus 40   
GUICreateFloatingPopup 40   
GUITrackFloatingPopup 40   
GUIGetMenuPopupCount 40   
GUIAppendMenuToPopup 40   
GUIInsertMenuToPopup 40   
Summary 41   
17. Text Handling Functions 41   
GUISetWindowText 41   
GUIGetWindowText 41   
GUIGetWindowTextLength 41   
GUIGetExtentX 41   
GUIGetExtentY 42   
GUIGetControlExtentX 42   
GUIGetControlExtentY 42   
GUIGetStringPos 43   
Summary 43   
18. Drawing functions 43   
GUIDrawLine and GUIDrawLineRGB 43   
SciTech Software, Inc.   
Open Watcom Linux Port Page 5 of 54   
GUI Software Requirements Specification   
GUIDrawBar 43   
Summary 44   
19. Font handling functions 44   
GUIFontsSupported 44   
GUIChangeFont 44   
GUIGetFontInfo 44   
GUISetFontInfo 44   
GUISetSystemFont 44   
GUIGetFontFromUser 44   
Summary 45   
20. Cursor functions 45   
GUISetMouseCursor 45   
GUIResetMouseCursor 45   
Summary 45   
21. Window functions 45   
GUIControlDirty 46   
GUIWndDirtyRow 46   
GUIWndDirtyRect 46   
GUIRefresh 46   
GUIBringToFront 46   
GUISetFocus 46   
GUIGetFocus 47   
GUIResizeWindow 47   
GUIIsMinimized and GUIIsMaximized 47   
GUIRestoreWindow 47   
GUIHideWindow 47   
GUIIsWindowVisible 47   
GUISetRestoredSize 47   
GUIGetRestoredSize 47   
GUISetIcon 48   
GUICascadeWindows 48   
Summary 48   
22. Hot spot functions 48   
GUIInitHotSpots 48   
GUIDrawHotSpot 48   
Summary 48   
23. Information functions 48   
GUIGetKeyState 49   
GUIGetPaintRect 49   
GUIGetAbsRect 49   
GUIGetAbsRect 49   
GUIGetMousePosn 49   
GUIGetMinSize 49   
GUIEnumChildWindows 50   
Summary 50   
24. Color functions 50   
Open Watcom Linux Port Page 6 of 54   
GUI Software Requirements Specification   
GUIGetRGBFromUser 50   
Summary 50   
25. Combo list/box functions 50   
GUIAddText 51   
GUISetListItemData 51   
GUIGetListItemData 51   
GUIAddTextList 51   
GUIInsertText 51   
GUIClearList 51   
GUIDeleteItem 51   
GUIGetListSize 51   
GUIGetCurrSelect 52   
GUISetCurrSelect 52   
GUIGetListItem 52   
GUILimitEditText 52   
GUIInsertMenuByID 52   
Summary 52   
26. Radio button and check box functions 52   
GUIIsChecked 52   
GUISetChecked 52   
Summary 53   
27. F1 key hook functions 53   
GUIHookF1 53   
GUIUnHookF1 53   
Summary 53   
28. Other functions. 53   
29. Type definitions 53   
30. Functions that are never used in the current code 54   
GUIDropDown 54   
GUIScrollCaret 54   
GUISetTopIndex 54   
GUIGetTopIndex 54   
GUISetHorizontalExtent 54   
GUIActivateNC 54

# GUI Software Requirements Specification

## Executive Summary

This document describes a detailed approach to porting low-level Open Watcom GUI library to Linux platform using GTK toolkit for the X Window System.

## 1. Introduction

## 1.1 About this document

This paper represents a result of the Open Watcom low level GUI library research. It provides porting guidelines and identifies the effort required to port the GUI library to Linux platform using GTK windowing toolkit for the X Window System. The research was based on the Open Watcom version 1.1.7

This paper is intended as a base Software Requirements Specification for the Open Watcom GUI porting project.

## 1.2 Document structure

This document consists of several parts.

“GTK Overview” provides a short overview of the GIMP Toolkit

“General GUI Porting Approach” describes a porting approach.

“Issues” identifies a set of possible caveats that should be considered before commencing the porting effort.

“Target System Requirements” provides information about required software on a target system for the ported library to run.

“Detailed Porting Guidelines and Estimation” provides detailed guidelines on porting each library function.

<table><tr><td>Open Watcom Linux Port</td><td>Page 8 of 54</td></tr><tr><td>GUI Software Requirements Specification</td><td></td></tr></table>

## 2. GTK Overview

GTK (GIMP Toolkit) is a library for creating graphical user interfaces. It is licensed using the LGPL license, so open software, free software, or commercial non-free software can be developed using GTK without having to spend costs on licenses or royalties.

It's called the GIMP toolkit because it was originally written for developing the GNU Image Manipulation Program (GIMP), but GTK has now been used in a large number of software projects, including the GNU Network Object Model Environment (GNOME) project. GTK is built on top of GDK (GIMP Drawing Kit) which is basically a wrapper around the low-level functions for accessing the underlying windowing functions (Xlib in the case of the X windows system), and gdk-pixbuf, a library for client-side image manipulation.

GTK is essentially an object oriented application ’programmers interface (API). Although written completely in C, it is implemented using the idea of classes and callback functions (pointers to functions).

There is also a third component called GLib which contains a few replacements for some standard calls, as well as some additional functions for handling linked lists, etc. The replacement functions are used to increase GTK's portability, as some of the functions implemented here are not available or are non-standard on other Unixes (one example being g\_strerror)(). Some also contain enhancements to the libc versions, such as g\_malloc() that has enhanced debugging utilities.

In version 2.0, GLib has picked up the type system which forms the foundation for GTK's class hierarchy, the signal system which is used throughout GTK, a thread API which abstracts the different native thread APIs of the various platforms and a facility for loading modules.

As the last component, GTK uses the Pango library for internationalized text output.

Why use GTK?

It is:

• Stable,

• Free,

• Fast,

• Well documented,

• Broadly adopted,

• Themes support,

• Extensible.

## 3. General GUI Porting Approach

The Watcom GUI library depends on the Watcom Programming Interface (WPI) and Memory Tracker (TrMem) libraries. WPI is explicitly designed to port Windows functionality to OS/2 Presentation Manager (not the other way around). Both Windows and OS/2 APIs have similar and compatible designs to a large extent. GTK API is similar neither to Windows nor to OS/2 API, so it would be ineffective to extend the WPI library with GTK support. However taking into account that the Watcom GUI library actively uses WPI calls it seems reasonable to port most of the WPI functions called in the library.

Since the GUI library relies on OS/2 PM and Windows API, it uses predefined types that exist only in these environments, such as HWND and HBRUSH. It will be an additional work for the programmer to add appropriate type definitions in a special file. For instance, HWND should be defined as GtkWidget\*, and HBRUSH should be defined as GdkStyle\*.

<table><tr><td>Open Watcom Linux Port</td><td>Page 9 of 54</td></tr><tr><td>GUI Software Requirements Specification</td><td></td></tr></table>

As long as in Windows and OS/2 environments user interface controls are placed according to the specified coordinates we must replicate this in GTK using the following widget hierarchy:

Window – Vertical Box – Scrolled Window – View Port – Fixed

![](images/9c20b2b415614fefae4a1ea1d34ea8be7e8fcd9f74cb171c7b3910af82510e7c.jpg)  
Fig.1 Widget hierarchy for a standard Open Watcom GUI window

<table><tr><td>Open Watcom Linux Port</td><td>Page 10 of 54</td></tr><tr><td>GUI Software Requirements Specification</td><td></td></tr></table>

![](images/fbfd7bd131c1ec93b9a94c903cb10a8fda081d5c71a9b50bc0bdc1ab52daedb1.jpg)  
Fig.2 Open Watcom IDE GTK prototype.

<table><tr><td>Open Watcom Linux Port</td><td>Page 11 of 54</td></tr><tr><td>GUI Software Requirements Specification</td><td></td></tr></table>

![](images/b3e0e16e2059d18e33f9d8fa24606ab3556d01ef7bdda91841d53066893d0a88.jpg)  
Fig 3. Open Watcom IDE GTK prototype

<table><tr><td>Open Watcom Linux Port</td><td>Page 12 of 54</td></tr><tr><td>GUI Software Requirements Specification</td><td></td></tr></table>

## 4. Issues

Due to the fact that Open Watcom itself is heavy oriented towards Windows, several issues should be considered and dealt with before commencing the porting effort.

## • Resource files

There is no possibility in GTK to handle the Windows or OS/2 – style resource files. GTK uses its own resource files which are very much different from those in Windows or OS/2 and allows to specify only styles and key bindings of the widgets. There is a possibility to overcome this issue to some extent by using libglade library which is used in GTK to build user interface described in the XML file. A utility can be written to extract all the necessary information from the Windows – OS/2 resource files and present it in the XML format which can be handled by libglade to build a user interface. However this will provide only a partial solution as there is nothing like String Table in libglade as string resources are handled by gettext library in GTK. Also there are no numeric resource identifiers in GTK. Problematic functions are: GUICreateResDialog(), GUICreateDialogFromRes() and GUILoadString().

## • MDI "Windows in Window" model

GTK has no possibility to implement applications with MDI "Windows in Window" model. However, it is possible to assign a parent for windows, and they will be destroyed when the parent is closed.

## • Help subsystem

GTK has no built in user help subsystem, as this level of user interaction is handled by desktop environments. Problematic functions here are: GUIHelpInit(), GUIHelpFini(), GUIShowHelp(), GUIDisplayHelp(), GUIDisplayHelpWin4() and GUIDisplayHelpId().

Other issues to consider include:

• Numeric identifiers of widgets.

• Specific approach to window building includes Window Classes and Dialog Templates.

• The toolkit allows modifying window (system) menu, which is impossible in GTK.

<table><tr><td>Open Watcom Linux Port</td><td>Page 13 of 54</td></tr><tr><td>GUI Software Requirements Specification</td><td></td></tr></table>

## 5. Target System Requirements

GTK is broadly adopted among the major Linux distribution vendors including RedHat, SuSE, TurboLinux. So, in general case deployment of the ported library should not be a problem. In case the target distribution does not support GTK at all or uses incompatible or older versions of the toolkit the library can be linked statically, the drawback of this approach will be an increased size of the library.

In situations when the library would be shipped in source files and then compiled, target system will have to satisfy to a number of requirements. Namely it must have a C compiler and an X Window System including the following libraries:

• pkg-config (only for compilation)

• GNU make (only for compilation)

• JPEG, PNG and TIFF image libraries

• FreeType

• fontconfig

• GNU libiconv library

• GNU gettext

GLib

• Pango

ATK

• GTK+

Open Watcom Linux Port Page 14 of 54   
GUI Software Requirements Specification

## Detailed Porting Guidelines and Estimation

## Initial Stage

## 6. GUI Library Initialization.

GUI library initialization procedure starts from GUIXMain() function called from predefined in the library main().

Below is the list of subsequent function calls originated from GUIXMain().

GUIXMain()   
GUIStoreArgs()   
GUISetWindowClassName()   
GUIGetWindowClassName()   
\_wpi\_setwpiinst()   
GUIMemOpen()   
GUIFirstCrack()   
SetupClass()   
GUILoadStrInit()   
GUIGetExtName()   
GUIInitInternalStringTable()   
GUIInitGUIMenuHint()   
GUIGetFront()   
GUIWinMessageLoop()   
GUICleanup()   
GUIDeath()   
GUICleanupHotSpots()   
GUIFreeStatus()   
GUIFiniInternalStringTable()   
GUILoadStrFini()   
GUISysFini()   
GUIFiniDialog()   
GUIFree()   
GUIDead()   
GUIMemClose()

Majority of these functions does not need to be changed, GUISetWindowClassName() and GUIGetWindowClassName() is not needed for GTK port at all, since GTK has no window classes.

The following functions should be ported:

GUIXMain() – 0.5 hour(s)   
SetupClass() - 0.5 hour(s)   
\_wpi\_postquitmessage() – 0.5 hour(s)   
GUILoadStrInit() – 0.5 hour(s)   
GUIWinMessageLoop() – 1 hour(s)

## GUIXMain

The only function called form the main(). It initializes program GUI, processes message queue and finishes the program.

SciTech Software, Inc.

<table><tr><td>Open Watcom Linux Port</td><td>Page 15 of 54</td></tr><tr><td>GUI Software Requirements Specification</td><td></td></tr></table>

Time needed for porting: 0.5 hours.

## SetupClass

Registers a window class.

There are no window classes in GTK, so this function should be empty for the GTK port.

Time needed for porting: 0.5 hours.

## \_wpi\_postquitmessage

Post QUIT message into the program.

This function should be empty in GTK port since there is no need to emit QUIT message if message loop is not started.

Time needed for porting: 0.5 hours.

## GUILoadStrInit

Load external resource DLL under Windows, and set GUIMsgInitFlag.

Since there is no "external resource DLLs" in Linux, the GTK port should do the same that OS/2 port does, namely, just set GUIMsgInitFlag.

Time needed for porting: 0.5 hours.

## GUIWinMessageLoop

Starts the main program loop.

In GTK program message loop strats with gtk\_main().

Time needed for porting: 1 hour.

## Summary

3 hours are needed for porting and, additionally, approximately 3 more hours are needed for testing and tuning, totaling to 6 hours for this part.

At the completion of this step we will be able to execute the following code.

int

GUImain() {}

Open Watcom Linux Port Page 16 of 54   
GUI Software Requirements Specification

## 7. Display window initialization

In order to initialize the library, programmer should call GUIWndInit() function.

Below is the list of subsequent function calls originated from GUIWndInit().

GUIWndInit()   
GUISysInit()   
wpi\_setdoubleclicktime()   
GUISetScreen()   
GUIInitDialog()   
GUIStrDup()   
GUIAlloc()   
DialogTemplate()   
DoneAddingControls()   
DynamicDialogBox()   
GUIInitDialogFunc()   
\_wpi\_enddialog()   
The following functions should be ported:   
GUIWndInit()– 1 hour(s)   
\_wpi\_setdouibleclicktime() – 0.5 hour(s)   
GUIInitDialogFunc() – 4 hour(s)   
\_wpi\_enddialog() – 1 hour(s)   
GUIWndInit   
High level function for the library initialization.   
It is needed to use gdk\_screen\_get\_width() and gdk\_screen\_get\_height() applied to the   
result of gdk\_screen\_get\_default()in order to retrieve screen width and high, instead of   
\_wpi\_get\_systemmetric().   
Time needed for porting: 1 hour(s).   
\_wpi\_setdouibleclicktime   
Sets the double click time.   
Programmer should use gdk\_set\_double\_click\_time()   
Time needed for porting: 0.5 hour(s).   
GUIInitDialogFunc   
Callback function the test dialog box used to get the dialog box font and client size information.   
In GTK it is possible to get the dialog box font from the style returned by   
gtk\_widget\_get\_default\_style().   
Instead of\_wpi\_getclientrect(), \_wpi\_getwidthrect() and \_wpi\_getheightrect()   
functions the gtk\_widget\_get\_request\_size() should be called.   
Time needed for porting: 4 hour(s).   
\_wpi\_enddialog   
This function is used to dismiss a dialog. Note, that this does not destroy the dialog by default but only   
hides the dialog.

SciTech Software, Inc.

<table><tr><td>Open Watcom Linux Port</td><td>Page 17 of 54</td></tr><tr><td>GUI Software Requirements Specification</td><td></td></tr></table>

The similar behaviour could be achieved in GTK by emitting "delete\_event" to the given window.   
g\_signal\_emit() or g\_signal\_emit\_by\_name() should be used.

Time needed for porting: 1 hour(s).

## Summary

6.5 hours are needed for porting activity and, additionally, approximately 3.5 hours are needed for testing and tuning. This step requires 10 hours. At the end of this step we will be able to execute the following code.

int   
GUImain() {   
GUIWndInit(250);   
}

## 8. Window creation

This step requires Resource Files handling implemented (see “Issues” section).

Below is the list of subsequent function calls originated from GUICreateWindow().

GUICreateWindow()   
GUISetupWnd()   
GUIXSetupWnd()   
GUIXCreateWindow()   
GUISetupStruct()   
GUICalcLocation()   
GUIScaleToScreen()   
GUIConvertRect()   
GUIConvert()   
GUIMulDiv()   
GUIScaleToScreenR()   
GUIConvertRect()   
GUIConvert()   
GUIMulDiv()   
\_wpi\_getclientrect()   
\_wpi\_getheightrect()   
\_wpi\_cvtc\_y\_size\_plus1()   
\_wpi\_cvtc\_y()   
\_wpi\_getclientrect()   
\_wpi\_getheightrect()   
GUISetColours()

en Watcom Linux Port Page 18 of 54   
I Software Requirements Specification   
GUIXSetColours()   
SetBKBrush()   
GUIGetRGB()   
FillInRGB()   
GetRValue()   
GetGValue()   
GetBValue()   
GUIRGB()   
\_wpi\_createsolidbrush()   
\_wpi\_loadmenu()   
GUICreateMenus()   
\_wpi\_createmenu()   
AppendMenus()   
GUICreateSubMenu()   
GUICreateMenuFlags()   
\_wpi\_appendmenu()   
AppendMenu()   
InsertMenu()   
InsertPopup()   
GetPopupHMENU()   
GetParentOffset()   
\_wpi\_getmenuitemcount()   
\_wpi\_getsubmenu()   
GUIGetHMENU()   
\_wpi\_get\_systemmenu()   
\_wpi\_get\_menu()   
GUIInitHint()   
GetStructNum()   
CountMenus()   
InsertHint()   
GUISetGUIHint()   
\_wpi\_create\_window\_ex()   
GUISetRedraw()   
\_wpi\_setredraw()   
GUIMaximizeWindow()

SciTech Software, Inc.

Open Watcom Linux Port Page 19 of 54   
GUI Software Requirements Specification   
GUIMinimizeWindow()   
\_wpi\_showwindow()   
GUIShowWindowNA()   
GUIInvalidatePaintHandles()   
GUIFreeWndPaintHandles()   
GUIInitMDI()   
GUIIsValidWindow()   
GUIGetFront()   
GUIGetNextWindow()   
InList()   
GUIFreeWindowMemory()   
It is impossible to implement \_wpi\_loadmenu() and GUICreateMenus() on GTK because GTK doesn't   
support OS/2-like resource files and has no possibility to modify window (system) menu.   
Refer to the “Issues” section.   
The following functions should be ported:   
GUIXCreateWindow() – 4 hour(s)   
GUICalcLocation() – 2 hour(s)   
\_wpi\_createsolidbrush() – 2 hour(s)   
\_wpi\_create\_window\_ex() – 4 hour(s)   
\_wpi\_setredraw() – 1 hour(s)   
GUIMaximizeWindow() – 1 hour(s)   
GUIMinimizeWindow() – 1 hour(s)   
\_wpi\_showwindow() – 1 hour(s)   
GUIShowWindowNA() – 1 hour(s)   
GUIFreeWindowMemory() – 2 hour(s)   
IXCreateWindow   
This high level function creates a window widget and applies the passed parameters to it.   
Despite the fact that all the low-level functionality is performed by sub-calls, some tweaking may be   
needed.   
Time needed for porting: 4 hours.   
ICalcLocation   
This function calculates coordinates of the new window. Note that X Window System window managers   
are free to ignore this; most window managers ignore requests for initial window placement (using a user  
defined placement algorithm instead) and honors requests only after the window has been shown.   
Instead of using \_wpi\_getclientrect() to get client area coordinates of the window, programmers   
should use gtk\_widget\_get\_request\_size().   
Time needed for porting: 2 hours.

<table><tr><td>Open Watcom Linux Port</td><td>Page 20 of 54</td></tr><tr><td>GUI Software Requirements Specification</td><td></td></tr></table>

## \_wpi\_createsolidbrush

In Windows this returns a solid brush with color. In OS/2 PM this allocates space for the object structure and sets the foreground colour for the brush.

For GTK this should create GtkStyle structure with the given parameters.

Time needed for porting: 2 hours.

## \_wpi\_create\_window\_ex

This function returns pointer to newly created window widget with the given parameters.

When ported, this function should make a call of gtk\_window\_new(), and apply parameters passed in info. After the window is created, it is necessary to put GtkScrolledWindow widget in it and then put GtkFixed widget in the scrolled window widget. See “General Porting Approach” section.

Time needed for porting: 4 hours.

## \_wpi\_setredraw

This function enables/disables window updates.

Should be done via gdk\_window\_thaw\_updates() and gdk\_window\_freeze\_updates()

Time needed for porting: 1 hour.

## GUIMaximizeWindow

This function maximizes the specified window.

In order to ask the window manager to maximize the window in GTK gtk\_window\_maximize() should be called.

Time needed for porting: 1 hour.

## GUIMinimizeWindow

This function minimizes the specified window.

In order to ask window manager to minimize the window in GTK, gtk\_window\_minimize() should be called.

Time needed for porting: 1 hour.

## \_wpi\_showwindow

Shows the window according to the given state. Windows predefined states are used.

In the GTK gtk\_widget\_show() and gtk\_window\_hide() should be used.

Time needed for porting: 1 hour.

## GUIShowWindowNA

Shows the window.

gdk\_window\_show() should be used

Time needed for porting: 1 hour.

## GUIFreeWindowMemory

Frees all resources related to the given window.

In GTK gtk\_object\_destory() should be called which automatically will destroy all children. Some additional tweaking may be needed.

SciTech Software, Inc.

Open Watcom Linux Port Page 21 of 54   
GUI Software Requirements Specification

Time needed for porting: 2 hours.

## Summary

19 hours are needed for porting activity and, additionally, approximately 16 more hours are needed for testing and tuning. This step requires 35 hours. At the finish of this step we will be able to execute the following code.

```c
#include "gui.h"
#include "guitypes.h"
static gui_rect Scale = { 0, 0, 1000, 1000 };
bool MainEventWnd( gui_window *gui, gui_event gui_ev, void *param )
{
gui = gui;
gui_ev = gui_ev;
param = param;
return( TRUE );
}
static gui_create_info Parent = {
"Sample Application",
{ 250, 250, 500, 500 },
GUI_HSCROLL | GUI_VSCROLL,
GUI_GADGETS | GUI_VISIBLE,
NULL,
0, NULL,
0, NULL,
&MainEventWnd,
NULL,
NULL,
0
};
static gui_create_info Child = {
"Child Window",
{ 300, 300, 200, 200 },
GUI_SCROLL_BOTH,
GUI_VISIBLE+GUI_CLOSEABLE+GUI_MAXIMIZE+GUI_RESIZEABLE+GUI_MINIMIZ
NULL,
0,
NULL,
0, NULL,
&MainEventWnd,
NULL,
NULL,
0
};
void GUImain( void )
{
GUIMemOpen();
GUIWndInit( 300, GUI_GMOUSE );
GUISetScale( &Scale );
Child.parent = GUICreateWindow( &Parent );
```

SciTech Software, Inc.

Open Watcom Linux Port Page 22 of 54   
GUI Software Requirements Specification

```objectivec
GUICreateWindow( &Child );
}
```

## 9. Standard sample

The next objective is to run a standard Watcom GUI sample program located in gui/sample/samp2.c.

Below is its listing.

```c
#include <string.h>
#include "gui.h"
#define TRUE 1
#define FALSE 0
#define HEIGHT 5
#define WIDTH 8
static gui_ord Width = 0;
#define NUM_TEXT 5
static char Text[][NUM_TEXT] = { {"0%"}, {"25%"}, {"50%"}, {"75%"}, {"100%"}
};
static int Strlen[NUM_TEXT] = { 2, 3, 3, 3, 4 };
static GUICALLBACK GetNewFunction;
static GUICALLBACK StatusFunction;
static gui_create_info DialogWnd = {
"Install Program: ",
{ 20, 20, 40, 40 },
GUI_NOSCROLL,
GUI_VISIBLE,
NULL,
0,
NULL,
0,
NULL,
&GetNewFunction,
NULL,
0
};
static gui_rect Rect;
static int Row;
static int NumEnters = 0;
static gui_colour_set StatusColours[GUI_NUM_ATTRS+1] = {
/* Fore Back */
GUI_BLUE, GUI_WHITE, /* GUI_MENU_PLAIN */
GUI_BLUE, GUI_WHITE, /* GUI_MENU_STANDOUT */
GUI_BLUE, GUI_WHITE, /* GUI_BACKGROUND */
GUI_BLUE, GUI_WHITE, /* GUI_TITLE_ACTIVE */
GUI_GREY, GUI_WHITE, /* GUI_TITLE_INACTIVE */
```

SciTech Software, Inc.

```c
Open Watcom Linux Port Page 23 of 54
GUI Software Requirements Specification
GUI_BLUE, GUI_WHITE, /* GUI_FRAME_ACTIVE */
GUI_GREY, GUI_WHITE, /* GUI_FRAME_INACTIVE */
GUI_BRIGHT_WHITE, GUI_MAGENTA /* GUI_FIRST_UNUSED */
};
static gui_create_info StatusWnd = {
"Percent of Installation Complete",
{ 19, 70, 42, 20 },
GUI_NOSCROLL,
GUI_VISIBLE | GUI_DIALOG_LOOK,
NULL,
0,
NULL,
GUI_NUM_ATTRS + 1,
&StatusColours,
&StatusFunction,
NULL,
0
};
enum {
ctr_static,
ctr_edit,
ctr_cancelbutton,
ctr_okbutton
};
static gui_control_info GetNew[] = {
{ GUI_STATIC, "Please enter install path:", { 4, 4, 30,
HEIGHT }, NULL, GUI_NOSCROLL, GUI_NONE, ctr_static },
{ GUI_EDIT, NULL, { 4, 15, 30, HEIGHT }, NULL,
GUI_NOSCROLL, GUI_NONE, ctr_edit },
{ GUI_PUSH_BUTTON, "CANCEL", { 6, 30, WIDTH, HEIGHT }, NULL,
GUI_NOSCROLL, GUI_NONE, ctr_cancelbutton },
{ GUI_DEFPUSH_BUTTON, "OK", { 26, 30, WIDTH, HEIGHT }, NULL,
GUI_NOSCROLL, GUI_NONE, ctr_okbutton }
};
static gui_colour_set Colours[GUI_NUM_INIT_COLOURS] =
{
{ GUI_BRIGHT_WHITE, GUI_BLUE },
{ GUI_BRIGHT_WHITE, GUI_BLUE }
};
static char * text = NULL;
static gui_message_return ret_val = GUI_RET_CANCEL;
static gui_window * Status = NULL;
/*
* GetNewFunction - call back routine for the GetNewVal dialog
*/
static bool GetNewFunction( gui_window * gui, gui_event gui_ev, void * param
)
{
```

Open Watcom Linux Port Page 24 of 54   
GUI Software Requirements Specification

```c
unsigned id;
switch( gui_ev ) {
case GUI_INIT_DIALOG :
ret_val = GUI_RET_CANCEL;
break;
case GUI_DESTROY :
if( Status != NULL ) {
GUIDestroyWnd( Status );
}
break;
case GUI_CLICKED :
GUI_GETID( param, id );
switch( id ) {
case ctr_cancelbutton :
GUICloseDialog( gui );
ret_val = GUI_RET_CANCEL;
break;
case ctr_okbutton :
text = GUIGetText( gui, ctr_edit );
if( Status == NULL ) {
Status = GUICreateWindow( &StatusWnd );
} else {
NumEnters ++;
Rect.width = ( NumEnters * Width ) / 4;
if( NumEnters > 4 ) {
GUICloseDialog( gui );
} else {
GUIWndDirty( Status );
}
}
ret_val = GUI_RET_OK;
break;
}
break;
}
return( TRUE );
}
/*
* StatusFunction - call back routine for the status window
*/
static bool StatusFunction( gui_window * gui, gui_event gui_ev,
)
{
int i;
int pos;
gui_text_metrics metrics;
param = param;
switch( gui_ev ) {
case GUI_INIT_WINDOW :
Row = GUIGetNumRows( gui ) / 2;
GUIGetTextMetrics( gui, &metrics );
```

SciTech Software, Inc.

Open Watcom Linux Port Page 25 of 54   
GUI Software Requirements Specification   
GUIGetClientRect( gui, &Rect );   
Rect.x = 1;   
Rect.y = 1;   
Width = Rect.width - 2 \* Rect.x;   
Rect.width = 0;   
for( i = 0; i < NUM\_TEXT; i++ ) {   
Strlen[i] \*= metrics.max.x;   
}   
break;   
case GUI\_DESTROY :   
break;   
case GUI\_PAINT :   
GUIDrawRect( gui, &Rect, GUI\_FIRST\_UNUSED );   
for( i = 0; i < NUM\_TEXT; i++ ) {   
pos = ( i \* Width / 4 ) - Strlen[i] + Rect.x;   
if( pos < (int)Rect.x ) {   
pos = Rect.x;   
}   
if( ( i > NumEnters ) ||   
( i == 0 ) && ( NumEnters == 0 ) ) {   
GUIDrawText( gui, &Text[i], Strlen[i], Row, pos,   
GUI\_TITLE\_ACTIVE );   
} else {   
GUIDrawText( gui, &Text[i], Strlen[i], Row, pos,   
GUI\_FIRST\_UNUSED );   
}   
}   
break;   
}   
return( TRUE );   
void GUImain( void )   
GUIMemOpen();   
GUIWndInit( 250 );   
GUICreateDialog( &DialogWnd, NUM\_CONTROLS, &GetNew );   
Here is a list of functions not yet described:   
GUICreateDialog()   
GUIDestroyWnd()   
GUIGetText()   
GUICloseDialog()   
GUIWndDirty()   
GUIGetNumRows() (doesn't need to be ported)   
GUIGetTextMetrics()   
GUIGetClientRect()   
GUIDrawRect()   
SciTech Software, Inc

GUIDrawText().   
Below is the list of subsequent function calls.   
GUICreateDialog()   
CreateDlg()   
GUISetupWnd()   
GUIXCreateDialog()   
GUISetupStruct()   
GUIDoCreateResDialog()   
AdjustForFrame()   
AdjustToDialogUnits()   
ToDialogUnits()   
GUIDlgCalcLocation()   
GUISetControlStyle()   
DialogTemplate()   
AddControl()   
GUIControlInsert()   
DoneAddingControls()   
DynamicDialogBox()   
GUIDialogFunc()   
GUIFreeWindowMemory()   
GUIDestroyWnd()   
GUIGetText()   
GUIGetControlClass()   
GUIGetControlByID()   
GUICloseDialog()   
GUISendMessage()   
GUIWndDirty()   
GUIGetFront()   
GUIGetNextWindow()   
GUIGetParentFrameHWND()

<table><tr><td>Open Watcom Linux Port</td><td>Page 26 of 54</td></tr><tr><td>GUI Software Requirements Specification</td><td></td></tr></table>

SciTech Software, Inc.

<table><tr><td>Open Watcom Linux Port</td><td>Page 27 of 54</td></tr><tr><td>GUI Software Requirements Specification</td><td></td></tr></table>

GUIGetTextMetrics()   
GUIGetMetrics()   
GUIGetTheDC()   
GUIReleaseTheDC()   
GUISetMetrics()   
GUIScreenToScaleR()   
GUIConvert()   
GUIGetClientRect()   
\_wpi\_mapwindowpoints()   
\_wpi\_getwrectvalues()   
\_wpi\_getheightrect()   
GUIClientToScaleRect()   
GUIScreenToScaleRect()   
GUIConvertRect()   
GUIDrawRect   
DrawRect()   
GUIGetScrollPos()   
GUIDrawText()   
GUIGetTextMetrics()   
GUIXDrawText()   
GUIDrawTextBitmapAttr()   
GUIGetFore()   
GUIGetBack()   
GUIDrawTextBitmapRGB()

## GUIXCreateDialog

Creates a dialog with specified controls.

Instead of calling GlobalFree() here the window should be destroyed with gtk\_widget\_destroy() Some tweaking may be needed.

Time needed for porting: 1 hour.

<table><tr><td>Open Watcom Linux Port</td><td>Page 28 of 54</td></tr><tr><td>GUI Software Requirements Specification</td><td></td></tr></table>

## GUIDoCreateResDialog

Creates dialog defined in resource file.

Consider Issues section.

## DialogTemplate

Creates a dialog template.

There are no dialog templates in GTK. However, Open Watcom GUI Library adds controls to dialog templates, so we will create a dialog in this function. gtk\_window\_create() is needed to create a dialog.

Time needed for porting: 2 hours.

## AddControl

Adds control to the specified dialog template.

There is big amount of work here. This function should create all necessary controls, and apply specified attributes for every requested control.

Depending on type of the control and attributes various GTK functions should be used.

Time needed for porting: 8 hours.

## DoneAddingControls

Called when there are no more controls.

Should be empty in GTK port.

Time needed for porting: 0.5 hour.

## DynamicDialogBox

Creates a dynamic dialog box.

Should do nothing in GTK port, since DialogTemplate() function created the dialog.

Time needed for porting: 0.5 hour.

## GUIDialogFunc

Callback function for all dynamically created dialogs.

Should be rewritten for GTK version. The callback should correctly process resizing "resizerequest" and "close" events.

Time needed for porting: 2 hours.

## GUIDestroyWnd

Destroys the given window or all windows if NULL.

In GTK port, the function should call gtk\_widget\_destroy() for the given window or for the toplevel window if NULL.

Time needed for porting: 2 hours

## GUIGetText

Returns a copy of the text.

<table><tr><td>Open Watcom Linux Port</td><td>Page 29 of 54</td></tr><tr><td>GUI Software Requirements Specification</td><td></td></tr></table>

Should be greatly modified in GTK port, but it is a straightforward task. Text of almost all widgets could be retrieved via gtk\_label\_get\_label(), and gtk\_button\_get\_label(). Note that returned string will be owned by a widget and must not be modified or freed. So, it is needed to duplicate them in this function.

Selection of GtkTreeView could be accessed via gtk\_tree\_view\_get\_selection() function.

Time needed for porting: 6 hours.

## GUISendMessage

Sends a message to the specified window.

g\_signal\_emit() should be used for this purpose.

Time needed for porting: 1 hour.

## GUIWndDirty

Tells the user interface that interface should be repainted.

gdk\_window\_process\_updates() can repaint the window in GTK.

Time needed for porting: 1 hour.

## GUIGetMetrics

Returns text metrics for font of the given window.

GUIGetDC() and GUIReleaseDC should not be called in GTK port. There is no need to work on so low level in GTK. FontMetrics of the given window could be retrieved in the following way:

```c
PangoContext context = gtk_widget_get_pango_context(widget);
PangoFontMetrics metrics = pango_context_get_metrics(context,
widget->style->font_desk, pango_context_get_language(context));
g_memmove(&GUItm, metrics);
pango_font_metrics_unref(metrics);
```

Time needed for porting: 2 hours.

## GUIGetClientRect

Returns scaled, depending upon current scaling settings, rectangle of the given window in absolute coordinates.

Note, that client area of the window is the area of the GtkScrolledWindow widget placed in the window.

Time needed for porting: 1 hour.

## \_wpi\_mapwindowpoints

Translates coordinates relative to source widget's allocation to coordinates relative to destination widget's allocations.

The similar functionality in GTK should be achieved by

gtk\_widget\_translate\_coordinates(). Note that there is no definition similar to HWND\_DESKTOP in GTK. To get the needed value (root window of a given widget) gtk\_widget\_get\_root\_window() should be called for a given widget.

Time needed for porting: 2 hours.

<table><tr><td>Open Watcom Linux Port</td><td>Page 30 of 54</td></tr><tr><td>GUI Software Requirements Specification</td><td></td></tr></table>

## \_wpi\_getwrectvalues

Returns coordinates of the rectangle.

Should be rewritten using GdkRectangle type.

Time needed for porting: 0.5 hours.

## \_wpi\_getheightrect

Returns height of the given rectangle.

Should be rewritten using GdkRectangle structure.

Time needed for porting: 0.5 hours.

## DrawRect

Draws specified rectangle in the given window.

Should be rewritten. GTK paint functions applied to the GtkFixed widget placed in the window should be used for this purpose. This approach will allow avoiding all the sub-calls.

Time needed for porting: 4 hours.

## GUIXDrawText

Draws specified text in the given window.

Should be rewritten. pango\_layout\_set\_text() should be used for text rendering, and gtk\_paint\_layout() applied to GtkFixed widget placed in the window should be used for drawing. This approach will allow avoiding all the sub-calls.

Time needed for porting: 6 hours.

## Summary

41 hours are needed for porting activity and approximately 24 more hours are required for testing and tuning. This step requires 65 hours.

## Elaboration stage

## 10. Common control functions

There are a couple of common window control functions in the Open Watcom GUI Library. Below is the list of them with their sub-calls.

GUIAddControl()

GUIResizeControl()

GUIDeleteControl()

\_wpi\_destroywindow()

GUIControlDelete()

GUIDeleteCtrlWnd()

GUIEnableControl()

\_wpi\_enablewindow()

GUIIsControlEnabled()

SciTech Software, Inc.

<table><tr><td>Open Watcom Linux Port</td><td>Page 31 of 54</td></tr><tr><td>GUI Software Requirements Specification</td><td></td></tr></table>

\_wpi\_iswindowenabled()

## GUIAddControl

Adds a control to a window.

The function should create an appropriate control with appropriate styles and other attributes in the requested position. Already described AddControl should be used here.

Time needed for porting: 5 hours.

## GUIResizeControl

Set size and location of a control (relative parent).

Instead of using \_wpi\_getdlgitem() it is needed to use GUIGetControlByID() because the last is portable.

Instead of using \_wpi\_movewindow() it is needed to use gtk\_fixed\_move() to move the specified control in the fixed widget of window where the control is located.

Time needed for porting: 1 hour.

## \_wpi\_destroywindow

Destroys the given widget.

gtk\_widget\_destroy() should be called in GTK port.

Time needed for porting: 0.5 hour.

## GUIEnableControl

Sets control enabled or not enabled.

Instead of using \_wpi\_movewindow() it is need to use gtk\_fixed\_move() to move the specified control in the fixed widget of window where the control is located.

Time needed for porting: 1 hour.

## \_wpi\_enablewindow

Sets specified widget enabled or disabled.

gtk\_widget\_set\_sensitive() should be called within this function.

Time needed for porting: 0.5 hour.

## GUIIsControlEnabled

Checks if control is enabled.

<table><tr><td>Open Watcom Linux Port</td><td>Page 32 of 54</td></tr><tr><td>GUI Software Requirements Specification</td><td></td></tr></table>

Instead of using \_wpi\_movewindow() it is needed to use gtk\_fixed\_move() to move the specified control in the fixed widget of window where the control is located.

Time needed for porting: 1 hour.

## \_wpi\_iswindowenabled

Checks if the given widget is enabled.

gtk\_widget\_get\_sensitive() should be called within this function.

Time needed for porting: 0.5 hour.

## GUIGetControlRect

Gets location of a control relative to the parent.

Instead of using \_wpi\_movewindow() it is needed to use gtk\_fixed\_move() to move the specified control in the fixed widget of window where the control is located.

Instead of using GUIGetRelRect() it is needed to use g\_object\_get\_property() to read the coordinates of the control, and use gtk\_widget\_get\_size\_request() to get its size.

Time needed for porting: 2 hours.

## \_wpi\_showwindow

Shows or hides widget depending upon the flag.

Depending upon the flag gtk\_widget\_show\_all() or gtk\_widget\_hide\_all() function should be called.

Time needed for porting: 1 hour.

## \_wpi\_iswindowwisible

Checks if the widget is visible.

Property "visible" should be used to test if the widget is visible.

Time needed for porting: 1 hour.

## Summary

13.5 hours are needed for porting activity and, additionally, approximately 13.5 hours are required for testing and tuning. This step requires about 27 hours.

## 11. Common text functions

Below is the list of the common text related functions.

GUISetText()

GUIClearText()

GUISelectAll()

GUISetEditSelect()

GUIGetEditSelect()

GUIDlgBuffGetText()

## GUISetText

Sets the text of the given widget to the given text.

SciTech Software, Inc.

<table><tr><td>Open Watcom Linux Port</td><td>Page 33 of 54</td></tr><tr><td>GUI Software Requirements Specification</td><td></td></tr></table>

Depending on the class of the given widget gtk\_entry\_set\_text() or

gtk\_label\_set\_label() should be used.

Time needed for porting: 4 hours.

## GUIClearText

Clears the text.

GUISetText() should be called to perform the operation.

Time needed for porting: 0.5 hour.

## GUISelectAll

Selects the text within the controls GUI\_EDIT or GUI\_EDIT\_COMBOBOX.

Should call gtk\_editable\_select() applied to a valid GtkEntry widget to perform the operation.

Time needed for porting: 4 hours.

## GUISetEditSelect

Selects the portion of text within controls GUI\_EDIT or GUI\_EDIT\_COMBOBOX.

Should call gtk\_editable\_select() applied to valid GtkEntry widget to perform the operation.

Time needed for porting: 2 hours.

## GUIGetEditSelect

Finds out the portion of the text selected within GUI\_EDIT or GUI\_EDIT\_COMBOBOX.

Should call gtk\_editable\_get\_selection\_bounds() and gtk\_editable\_get\_chars() applied to valid GtkEntry widget to perform the operation.

Time needed for porting: 4 hours.

## GUIDlgBuffGetText

Gets text from the control into a buffer.

Additional investigation is needed in order to find out, whether the current memory allocation algorithm in Open Watcom GUI Library can be reused in the GTK port.

Time needed for porting: 1 hour.

## Summary

15.5 hours are needed for porting activity and, additionally, approximately 8.5 hours are needed for testing and tuning. This step requires about 24 hours.

Open Watcom Linux Port Page 34 of 54   
GUI Software Requirements Specification

## 12. Special dialogs functions

Below is the list of functions related to special dialogs with their sub-calls.

```autoit
GUIDisplayMessage
GUIGetNewVal()
GUIDlgOpen()
DlgOpen()
GUIGetDlgTextMetrics()
GUITruncToPixel()
DlgSetSize()
GUIGetSystemMetrics()
DlgSetCtlSizes()
GUICreateSysModalDialog()
GUICreateDialog()
GUIDlgPickWithRtn()
GUIDlgOpen()
GUIDlgPick()
GUIDlgPickWithRtn()
GUIGetFileName()
```

## GUIDisplayMessage

Displays a message and gets the response. Identical functionality could be achieved by using GTK's message dialog via gtk\_message\_new().

Time needed for porting: 4 hours.

## DlgOpen

Calls GUICreateDilog(), formatting locations to look good on every OS.

Some effort to make the controls look similar in Linux to all other systems will be needed.

Time needed for porting: 4 hours

## GUIGetDlgTextMetrics

Gets the metrics of the dialog font.   
FontMetrics of the given window could be retrieved in the following way:   
PangoContext context = gtk\_widget\_get\_pango\_context(widget);   
PangoFontMetrics metrics = pango\_context\_get\_metrics(context,   
widget->style->font\_desk, pango\_context\_get\_language(context));   
g\_memmove(&GUItm, metrics);   
pango\_font\_metrics\_unref(metrics);   
Time needed for porting: 2 hours.

<table><tr><td>Open Watcom Linux Port</td><td>Page 35 of 54</td></tr><tr><td>GUI Software Requirements Specification</td><td></td></tr></table>

## GUIGetSystemMetrics

Selects the text within GUI\_EDIT or GUI\_EDIT\_COMBOBOX.

Instead of calling \_wpi\_getsystemmetrics() the function should call various GTK functions to get different values.

Time needed for porting: 10 hours.

## DlgSetCtlSizes

Sets sizes of controls in GUIDlgOpen.

Some effort to make the controls look similar in all systems will be needed.

Time needed for porting: 2 hours.

## GUIGetEditSelect

Finds out the portion of text selected within GUI\_EDIT or GUI\_EDIT\_COMBOBOX.

Should call gtk\_editable\_get\_selection\_bounds() and gtk\_editable\_get\_chars() applied to valid GtkEntry widget to perform the operation.

Time needed for porting: 4 hours.

## GUIDlgBuffGetText

Gets text from the control into a buffer.

Additional research should be performed in order to find out whether Open Watcom GUI Library memory allocation algorithm can be reused in the GTK port.

Time needed for porting: 1 hour.

## Summary

27 hours are needed for porting activity and approximately 44 more hours are needed for testing and tuning. This step requires about 71 hour.

## 13. Scrolling functions

GUIInitHScrollCol()

GUIInitVScrollRow()

GUISetHScrollCol()

GUISetVScrollRow()

GUIGetHScrollCol()

GUIGetVScrollRow()

GUISetHScrollRangeCols()

GUISetVScrollRangeRows()

GUIGetHScrollRangeCols()

GUIGetVScrollRangeRows()

GUIDoHScroll()

GUIDoVScroll()

SciTech Software, Inc.

Open Watcom Linux Port Page 36 of 54   
GUI Software Requirements Specification   
GUIDoHScrollClip()   
GUIDoVScrollClip()   
GUIInitHScroll()   
GUIInitVScroll()   
GUISetHScroll()   
GUISetVScroll()   
GUIGetHScroll()   
GUIGetVScroll()   
GUISetHScrollRange()   
GUISetVScrollRange()   
GUIGetHScrollRange()   
GUIGetVScrollRange()   
GUISetHScrollThumb()   
GUISetVScrollThumb()

## Common guidelines

WGL windows of the GTK port mush have GTKScroledWindow in them. This should contain GTKViewPort that contains GtkFixed.

Values of the scroll bars could be set and get via gtk\_scrolled\_window\_set\_hajustment(),   
gtk\_scrolled\_window\_set\_vajustment(),   
gtk\_scrolled\_window\_get\_hajustment() and   
gtk\_scrolled\_window\_get\_vajustment() functions.

Since the scroll bars behavior is automatic, there is no possibility to set/get scroll bar range values. Required values could be achieved by getting width and height of the GtkFixed widget. Setting range of a scroll means resizing of the GtkFixed widget.

Page size could be obtained from size of the GtkViewPort widget.

## Summary

16 hours are needed for the porting activity and 16 more hours are required for for testing and tuning. This step requires about 32 hours.

## 14. Status window functions

```autoit
GUICreateStatusWindow()
GUICloseStatusWindow()
GUIHasStatus()
GUIDrawStatusText()
GUIClearStatusText()
GUIResizeStatusWindow()
```

## Common guidelines

WGL windows of the GTK port mush have GTKStatus widget in them. All these functions will interact with it.

SciTech Software, Inc.

<table><tr><td>Open Watcom Linux Port</td><td>Page 37 of 54</td></tr><tr><td>GUI Software Requirements Specification</td><td></td></tr></table>

## GUICreateStatusWindow

Creates a status window.

Should make the GtkStatus visible using gtk\_widget\_show().

Time needed for porting: 1 hour.

## GUICloseStatusWindow

Closes the status window.

Should make the GtkStatus invisible using Gtk\_widget\_hide()

Time needed for porting: 1 hour.

## GUIDrawStatusText

Draws the text to the status window.

Should use gtk\_status\_push().

Time needed for porting: 1 hour.

## GUIResizeStatusWindow

Resizes the status window.

It is impossible to change X position of the GtkStatus in our layout; however it is never changed through all Open Watcom sources. In addition, it isn't necessary to change vertical size of the bar because it is done automatically. So, this function can be empty in the GTK port.

Time needed for porting: 1 hour.

## Summary

4 hours are required for the porting activity and, additionally, 4 hours are required for testing and tuning.   
This step requires about 8 hours.

## 15. Toolbar functions

GUICreateFloatToolBar()   
GUICreateToolBar()   
GUICloseToolBar()   
GUIHasToolBar()   
GUIChangeToolBar()   
GUIToolBarFixed()

## Common guidelines

WGL windows of the GTK port mush have GtkHandleBox widget which contains GtkToolbar widget in itself. All these functions will interact with it.

## GUICreateFloatToolBar

Does the same as GUICreateToolbar() which is described below.

## GUICreateToolBar

Creates a tool bar.

Should make the GtkHandleBox visible using gtk\_widget\_show()

Time needed for porting: 1 hour.

SciTech Software, Inc.

<table><tr><td>Open Watcom Linux Port</td><td>Page 38 of 54</td></tr><tr><td>GUI Software Requirements Specification</td><td></td></tr></table>

## GUICloseToolBar

Closes the status window.

Should make the GtkHandleBox invisible using gtk\_widget\_hide()

Time needed for porting: 1 hour.

## GUIChangeToolBar

Changes the tool bar. Makes it fixed or floating.

To make the tool bar fixed it is needed to make GtkHandleBox invisible and set parent of the GtkToobar to parent of GtkHandleBox. To reverse the operation it is needed to make the GtkHandleBox visible and set parent of the GtkToobar to the GtkHandleBox widget.

Time needed for porting: 2 hours.

## Summary

4 hours are needed for porting activity and, additionally, approximately 6 more hours are needed for testing and tuning. This step requires about 10 hours.

## 16. Menu functions

GUIAppendMenu()   
GUIAppendMenuByOffset()   
GUIInsertMenu()   
GUIEnableMenuItem()   
GUICheckMenuItem()   
GUISetMenuText()   
GUISetHintText()   
GUIDeleteMenuItem()   
GUIResetMenus()   
GUIEnableMDIMenus()   
GUICreateFloatingPopup()   
GUITrackFloatingPopup()   
GUIGetMenuPopupCount()   
GUIAppendMenuToPopup()   
GUIInsertMenuToPopup()

## Common guidelines

WGL windows of the GTK port must have GtkMenuBar widget in them. All these functions will interact with it.

## GUIAppendMenu

Appends a menu to the menu bar.

gtk\_menu\_shell\_append() should be used to add the menu to GtkMenuBar widget. Floating status could be adjusted via “tear-off” state of the GtkMenu.

<table><tr><td>Open Watcom Linux Port</td><td>Page 39 of 54</td></tr><tr><td>GUI Software Requirements Specification</td><td></td></tr></table>

Additionally, the menu and all items should be added in global controls table via GUIControlInsert(), since GTK doesn't allow assigning ID to the menu items.

Time needed for porting: 2 hours.

## GUIAppendMenuByOffset

Appends sub menu to the menu.

gtk\_menu\_shell\_append() should be used to insert the menu to GtkMenu widget.

Additionally, the menu and all items should be added in global controls table via GUIControlInsert, since GTK doesn't allow assigning ID for the menu items.

Time needed for porting: 2 hours.

## GUIInsertMenu

Inserts a menu into the menu bar.

gtk\_menu\_shell\_insert() should be used to add the menu to GtkMenuBar widget. Floating status could be adjusted via tear-off state.

Additionally, the menu and all items should be added to the global controls table via GUIControlInsert(), since GTK doesn't allow to assign ID for the menu items.

Time needed for porting: 2 hours.

## GUIEnableMenuItem

Enables/disables menu item.

gtk\_widget\_set\_sensitive() applied to the appropriate GtkMenuItem should be used in this function. The GtkMenuItem widget can be obtained via GUIGetControlByID().

Time needed for porting: 2 hours.

## GUIEnableMenuItem

Checks/unchecks menu item.

gtk\_check\_menu\_item\_set\_active() applied to the appropriate GtkMenuItem should be used in this function. The GtkMenuItem widget can be obtained via GUIGetControlByID().

Time needed for porting: 2 hours.

## GUISetMenuText

Change the text of a menu item.

gtk\_label\_set\_label() applied to GtkLabel contained in appropriate GtkMenuItem should be used in this function. The GtkMenuItem widget can be obtained via GUIGetControlByID(). The GtkLabel widget could be obtained via gtk\_bin\_get\_child().

Time needed for porting: 2 hours.

## GUISetHintText

Sets the hint for the menu item.

gtk\_tooltips\_set\_tip() applied to GtkLabel contained in appropriate GtkMenuItem should be used in this function. The GtkMenuItem widget can be obtained via GUIGetControlByID(). The GtkLabel widget can be obtained via gtk\_bin\_get\_child().

Time needed for porting: 2 hours.

<table><tr><td>SciTech Software, Inc.</td></tr><tr><td></td></tr></table>

<table><tr><td>Open Watcom Linux Port</td><td>Page 40 of 54</td></tr><tr><td>GUI Software Requirements Specification</td><td></td></tr></table>

## GUIDeleteMenuItem

Delete a menu item for a pull down menu.

gtk\_widget\_destroy() applied to the appropriate GtkMenuItem should be used in this function.   
The GtkMenuItem widget can be obtained via GUIGetControlByID().

Time needed for porting: 2 hours.

## GUIResetMenus

Resets the entire menu structure for a window.

The function should destroy and create new GtkMenuBar. And, then, build and add given menu structure.

Time needed for porting: 6 hours.

## GUIEnableMDIMenus

Enables/disables the MDI menus.

Since the "Window in Window" MDI model is not possible in GTK. This function should do nothing for the GTK port.

Time needed for porting: 0.5 hour.

## GUICreateFloatingPopup

Creates a floating popup menu.

Should create a GtkMenu widget, and call GUITrackFloatingPopup.

Time needed for porting: 2 hours.

## GUITrackFloatingPopup

Tracks a floating popup menu.

gtk\_menu\_popup() applied to the appropriate GtkMenu should be used in this function. The GtkMenu widget can be obtained via GUIGetControlByID().

Time needed for porting: 2 hours.

## GUIGetMenuPopupCount

Returns number of items in the given floating popup menu.

gtk\_container\_get\_children() applied to the appropriate GtkMenu should be used in this function to obtain a list of the items. Then g\_list\_length() should be applied to the list to obtain a number of elements in the list. The GtkMenu widget can be obtained via GUIGetControlByID().

Time needed for porting: 2 hours.

## GUIAppendMenuToPopup

Appends sub menu to the given popup menu.

GUIAppendMenu() should be called in this function to perform the operation.

Time needed for porting: 2 hours.

## GUIInsertMenuToPopup

Inserts sub menu to the given popup menu.

GUIAppendMenuByOffset() should be called in this function to perform the operation.

<table><tr><td>Open Watcom Linux Port</td><td>Page 41 of 54</td></tr><tr><td>GUI Software Requirements Specification</td><td></td></tr></table>

Time needed for porting: 2 hours.

## Summary

32.5 hours are needed for the porting activity and, additionally, approximately 32.5 hours are required for testing and tuning. This step requires about 65 hours.

## 17. Text Handling Functions

GUISetWindowText()   
GUIGetWindowTextLength()   
GUIGetWindowText()   
GUIGetRow()   
GUIGetCol()   
GUIGetStringPos()   
GUIGetExtentX()   
GUIGetExtentY()   
GUIGetControlExtentX()   
GUIGetControlExtentY()   
GUIGetTextMetrics()   
GUIGetDlgTextMetrics()   
GUIGetPoint()   
GUIGetRow(), GUIGetCol(), GUIGetTextMetrics(), GUIGetDlgTextMetrics() and   
GUIGetPoint() does not need to be ported.   
GUISetWindowText   
Set window caption.   
gtk\_set\_window\_title() should be used here.   
Time needed for porting: 2 hours   
GUIGetWindowText   
Get window caption.   
gtk\_get\_window\_title() should be used here.   
Time needed for porting: 2 hours   
GUIGetWindowTextLength   
Get caption text length.   
In GTK the length of a char, pointer to which is returned by gtk\_get\_window\_title() can be   
measured.   
Time needed for porting: 2 hours   
GUIGetExtentX   
Finds X extent of the given string in current font.   
Width of the given string in specified window could be obtained in the following way.

<table><tr><td>SciTech Software, Inc.</td></tr></table>

```c
PangoLayout pango_layout = gtk_widget_create_layout(fixed, NULL);
pango_layout_set_text(pango_layout, text, text_len);
pango_layout_get_pixel_size(pango_layout, &width, NULL);
```

Open Watcom Linux Port Page 42 of 54   
GUI Software Requirements Specification

Where fixed is the GtkFixed widget located in the given window, text is the given text in the UTF-8 ecoding, text\_len is the length if the text, and width is variable for desired value.

Time needed for porting: 2 hours.

## GUIGetExtentY

Finds Y extent of the given string in current font.

Height of the given string in specified window could be obtained in the following way.

```c
PangoLayout pango_layout = gtk_widget_create_layout(fixed, NULL);
pango_layout_set_text(pango_layout, text, text_len);
pango_layout_get_pixel_size(pango_layout, NULL, &height);
```

Where fixed is the GtkFixed widget located in the given window, text is the given text in the UTF-8 ecoding, text\_len is the length if the text, and height is variable for desired value.

Time needed for porting: 2 hours.

## GUIGetControlExtentX

Finds X extent of the given string in font of the given control.

Width of the given string in specified window could be obtained in the following way.

```c
PangoLayout pango_layout = gtk_widget_create_layout(widget,
NULL);
pango_layout_set_text(pango_layout, text, text_len);
pango_layout_get_pixel_size(pango_layout, &width, NULL);
```

Where widget is the given widget returned by GUIGetControlByID located in the given window, text is the given text in the UTF-8 ecoding, text\_len is the length if the text, and width is variable for desired value.

Time needed for porting: 2 hours.

## GUIGetControlExtentY

Finds Y extent of the given string in font of the given control.

Height of the given string in specified window could be obtained in the following way.

PangoLayout pango\_layout = gtk\_widget\_create\_layout(widget,   
NULL);

```c
pango_layout_set_text(pango_layout, text, text_len);
pango_layout_get_pixel_size(pango_layout, NULL, &height);
```

Where widget is the given widget returned by GUIGetControlByID located in the given window, text is the given text in the UTF-8 encoding, text\_len is the length of the text, and height is variable for desired value.

Time needed for porting: 2 hours.

<table><tr><td>SciTech Software, Inc.</td></tr><tr><td></td></tr></table>

<table><tr><td>Open Watcom Linux Port</td><td>Page 43 of 54</td></tr><tr><td>GUI Software Requirements Specification</td><td></td></tr></table>

## GUIGetStringPos

Returns offset (in characters) of the given point if string is offset from left by given amount.

Calling of GUIGetTheDC() and DoReturn should be eliminated in this function as GTK operates at a higher level.

Time needed for porting: 1 hour.

## Summary

15 hours are needed for porting activity and, additionally, approximately 15 hours are needed for testing and tuning. This step requires about 30 hours.

## 18. Drawing functions

```autoit
GUIFillRect()
GUIDrawRect()
GUIDrawLine()
GUIFillRectRGB()
GUIDrawRectRGB()
GUIDrawLineRGB()
GUIDrawText()
GUIDrawTextPos()
GUIDrawTextExtent()
GUIDrawTextExtentPos()
GUIDrawTextRGB()
GUIDrawTextPosRGB()
GUIDrawTextExtentRGB()
GUIDrawTextExtentPosRGB()
GUIDrawBar()
GUIDrawBarGroup()
```

Since a couple of functions use other already ported functions, just a few of these functions needs modifications to make them work under GTK.

## GUIDrawLine and GUIDrawLineRGB

Draw a line given a gui\_attr or RGB and style information.

These functions use DrawLine() function which should be rewritten using gtk\_paint\_hline(), gtk\_paint\_vline() or gtk\_paint\_polygon().

Time needed for porting: 4 hour.

## GUIDrawBar

Draws the outline of a rectangle given a gui\_attr.

The function should use gtk\_paint\_bar() to perform the operation.

Time needed for porting: 4 hour.

<table><tr><td>Open Watcom Linux Port</td><td>Page 44 of 54</td></tr><tr><td>GUI Software Requirements Specification</td><td></td></tr></table>

## Summary

8 hours are needed for porting activity and, additionally, approximately 16 hours are needed for testing and tuning. This step requires about 24 hours.

## 19. Font handling functions

GUIFontsSupported() GUIChangeFont() GUIGetFontInfo() GUISetFontInfo() GUISetSystemFont() GUIGetFontFromUser()

## GUIFontsSupported

Returns TRUE if these font functions are supported.

All these functions except GUISetSystemFont() can be implemented. So,

GUIFontsSupported() should always return TRUE.

Time needed for porting: 0.5 hours.

## GUIChangeFont

Gets font choice from user and changes the font of the given window.

The function could be ported implemented with GUIGetFontFromUser() and GUISetFontInfo().

Time needed for porting: 2 hours.

## GUIGetFontInfo

Gets the font information for a window.

pango\_font\_description\_to\_string() applied to a style attribute of the given window should be used to perform the operation.

Time needed for porting: 2 hours.

## GUISetFontInfo

Sets the font information for a window.

The function should create PangoFontDescription via

pango\_font\_description\_from\_string() function, and modify style of the given window with gtk\_widget\_modify\_style().

Time needed for porting: 3 hours.

## GUISetSystemFont

Sets font to the system font (fixed or proportional).

It is impossible to implement this function in GTK. So, this function should do nothing in the GTK port.

Time needed for porting: 0.5 hours.

## GUIGetFontFromUser

Gets the font information from the user using a dialog.

<table><tr><td>SciTech Software, Inc.</td></tr></table>

SciTech Software, Inc.

<table><tr><td>Open Watcom Linux Port</td><td>Page 45 of 54</td></tr><tr><td>GUI Software Requirements Specification</td><td></td></tr></table>

This function should be implemented using standard GtkFontSelectionDialog().

Time needed for porting: 4 hours.

## Summary

12 hours are needed for porting activity and, additionally, approximately 12 hours are needed for testing and tuning. This step requires 24 hours.

## 20. Cursor functions

GUISetMouseCursor()

GUIResetMouseCursor()

## GUISetMouseCursor

Sets the type of mouse cursor.

This function should create an apropriate cursor with gdk\_cursor\_new(). And use gdk\_window\_set\_cursor() applied to the result of gdk\_get\_default\_root\_window() to change the cursor.

Time needed for porting: 2 hours.

## GUIResetMouseCursor

Resets the type of mouse cursor.

This function should use gdk\_window\_set\_cursor() applied to the result of gdk\_get\_default\_root\_window() and pass NULL as cursor type to change the cursor to default.

Time needed for porting: 2 hours.

## Summary

4 hours are needed for porting activity and 2 more hours are required for testing and tuning. This step requires about 6 hours.

## 21. Window functions

```autoit
GUIGetWindowColours()
GUIControlDirty()
GUIWndDirtyRow()
GUIWndDirtyRect()
GUIRefresh()
GUIActivateNC()
GUIBringToFront()
GUIGetRootWindow()
GUISetFocus()
GUIGetFocus()
GUIResizeWindow()
GUIIsMinimized()
GUIIsMaximized()
```

<table><tr><td>Open Watcom Linux Port</td><td>Page 46 of 54</td></tr><tr><td>GUI Software Requirements Specification</td><td></td></tr></table>

GUIRestoreWindow()

GUIHideWindow()

GUIShowWindow()

GUIIsWindowVisible()

GUISetRestoredSize()

GUIGetRestoredSize()

GUISetIcon()

GUICascadeWindows()

## GUIControlDirty

Causes refresh of the given control.

gdk\_window\_process\_updates() can repaint the control obtained via GUIGetControlByID().

Time needed for porting: 2 hours.

## GUIWndDirtyRow

Causes refresh of the given row.

gdk\_widget\_queue\_draw\_area() can repaint the window region. Note that calculation of the row coordinates is needed.

Time needed for porting: 3 hours.

## GUIWndDirtyRect

Causes refresh of the given rect.

gdk\_widget\_queue\_draw\_area() can repaint the window region.

Time needed for porting: 3 hours.

## GUIRefresh

Causes refresh of the screen.

gdk\_window\_process\_all\_updates() can repaint all windows.

Time needed for porting: 2 hours.

## GUIBringToFront

Bring the window to the top of all others.

Gdk\_window\_show() should be used.

Time needed for porting: 2 hours.

## GUISetFocus

Sets input focus to a control in a dialog box or in a window.

gtk\_window\_set\_focus() applied to the control obtained via GUIGetControlByID() should be used here.

Time needed for porting: 2 hours.

<table><tr><td>Open Watcom Linux Port</td><td>Page 47 of 54</td></tr><tr><td>GUI Software Requirements Specification</td><td></td></tr></table>

## GUIGetFocus

Finds out which main window has the focus.

This function makes no sense in GTK as it is impossible to implement an MDI in GTK. When ported – it will always return supplied parameter without modification.

Time needed for porting: 0.5 hour.

## GUIResizeWindow

Gives the window a new size and location.

gtk\_window\_move() should be called to move the window, and

gtk\_widget\_set\_size\_request() called to set a new size.

Note, that window managers are free to ignore the moving request; most window managers ignore request for initial window positions (instead using a user-defined placement algorithm) and honor requests after the window has already been shown.

Time needed for porting: 1 hour.

## GUIIsMinimized and GUIIsMaximized

Returns true if window is minimized/maximized.

gdk\_window\_get\_state() should be used to perform the operation.

Time needed for porting: 2 hours.

## GUIRestoreWindow

Restore window to pre-minimize or maximize size.

gdk\_window\_unmaximize() should be used to perform the operation.

Time needed for porting: 1 hour.

## GUIHideWindow

Hides the given window.

gdk\_window\_show() should be used to perform the operation.

Time needed for porting: 1 hour.

## GUIIsWindowVisible

Checks if the given window is visible.

gdk\_is\_window\_visible() should be used to perform the operation.

Time needed for porting: 1 hour.

## GUISetRestoredSize

Sets a size of the given window to a restored state.

gtk\_window\_set\_size() should be used to perform the operation.

Time needed for porting: 1 hour.

## GUIGetRestoredSize

Gets a size of the given window in a restored state.

gtk\_window\_get\_size() should be used to perform the operation.

SciTech Software, Inc.

<table><tr><td>Open Watcom Linux Port</td><td>Page 48 of 54</td></tr><tr><td>GUI Software Requirements Specification</td><td></td></tr></table>

Time needed for porting: 1 hour.

## GUISetIcon

Sets an icon for the given window.

gtk\_window\_set\_icon() should be used to perform the operation.

Time needed for porting: 2 hours.

## GUICascadeWindows

Arrange all child windows in MDI in cascade.

It is impossible to implement in GTK, so this function should just return TRUE.

Time needed for porting: 0.5 hour.

## Summary

25 hours are needed for the porting activity and, additionally, approximately 30 hours are required for testing and tuning. This step requires about 55 hours.

## 22. Hot spot functions

GUIInitHotSpots()

GUIGetNumHoSpots()

GUIGetHotSpotSize()

GUIDrawHotSpot()

## GUIInitHotSpots

Sets the bitmaps associated with user defined hot spots.

The function should create an array of GtkImage objects. Some code to convert bitmaps passed in function to some acceptable format will be needed.

Time needed for porting: 8 hours.

## GUIDrawHotSpot

Draws a hot spot at a given location.

The function should place the requested hot spot in the appropriate position with gtk\_fixed\_put() function.

Time needed for porting: 2 hours.

## Summary

10 hours are needed for porting activity and 6 more hours are needed for testing and tuning. This step requires about 16 hours.

## 23. Information functions

GUIGetKeyState()

GUISetExtra()

GUIGetExtra()

GUIGetClientRect()

SciTech Software, Inc.

GUIGetPaintRect()   
GUIGetAbsRect()   
GUIGetRect()   
GUIGetScrollStyle()   
GUIGetCreateStyle()   
GUIGetMousePosn()   
GUIGetSystemMetrics()   
GUIGetMinSize()   
GUIEnumChildWindows()   
GUIEnumControls()   
GUIGetArgs()

<table><tr><td>Open Watcom Linux Port</td><td>Page 49 of 54</td></tr><tr><td>GUI Software Requirements Specification</td><td></td></tr></table>

## GUIGetKeyState

Gets the current Shift-key state.

Since the function doesn't allow specifying which input device should be tested, it isn't clear.Shift key on which input device should be checked. However as this function is called only in event callbacks, it is possible to get the current Shift state of the input device which initiated the event via gdk\_keymap\_translate\_keyboard\_state() function.

## GUIGetPaintRect

The function uses \_wpi\_getpaintrect() which should be reimplemented for the GTK port to support GdkRectangle structure.

Time needed for porting: 2 hours.

## GUIGetAbsRect

Get a window size and location in absolute user defined units.

Windows size can be obtained via gtk\_window\_get\_size() function and position can be obtained via gtk\_window\_get\_position function.

Time needed for porting: 2 hours.

## GUIGetAbsRect

Get a window size and location relative to its parent.

The function should call GUIGetAbsRect().

Time needed for porting: 0.5 hours.

## GUIGetMousePosn

Gets the mouse position (in user coordinates).

gtk\_widget\_get\_pointer() function should be used to obtain the location of the mouse pointer in widget coordinates. Then the coordinates should be transformed relative to a WGL scaling factor.

Time needed for porting: 2 hours.

## GUIGetMinSize

Returns the smallest valid size for the window.

<table><tr><td>SciTech Software, Inc.</td></tr><tr><td></td></tr></table>

<table><tr><td>Open Watcom Linux Port</td><td>Page 50 of 54</td></tr><tr><td>GUI Software Requirements Specification</td><td></td></tr></table>

The function returns result based in MIN\_WIDTH and MIN\_HEIGHT definitions that are defined as 0. But in GTK windows may not be resized smaller that 1 by 1 pixels. So these definitions should be changed in the GTK port.

Time needed for porting: 0.5 hours.

## GUIEnumChildWindows

Enumerates child windows by calling given function with the gui\_window for each.

The function should call gdk\_window\_get\_children(), get the child's gui\_window via GUIFindWindowFromHWND, and call necessary callback.

Time needed for porting: 4 hours.

## Summary

11 hours are required for the porting activity and, additionally, 10 hours are required for testing and tuning.   
This step requires about 21 hours.

## 24. Color functions

GUISetWindowColours()

```autoit
GUISetWndColour()
```

```cmake
GUIGetRGBFromUser()
```

```autoit
GUIGetColourFromUser()
```

## GUIGetRGBFromUser

Creates dialog to ask user for color, returns its RGB.

GtkColorSelection() should used for this purpose.

Time needed for porting: 4 hours.

## Summary

4 hours are needed for porting activity and 2 more hours are needed for testing and tuning. This step requires about 6 hours.

## 25. Combo list/box functions

```autoit
GUIAddText()
GUISetListItemData()
GUIGetListItemData()
GUIAddTextList()
GUIInsertText()
GUIClearList()
GUIDeleteItem()
GUIGetListSize()
GUIGetCurrSelect()
GUISetCurrSelect()
GUIGetListItem()
```

SciTech Software, Inc.

<table><tr><td>SciTech Software, Inc.</td></tr></table>

<table><tr><td>Open Watcom Linux Port</td><td>Page 51 of 54</td></tr><tr><td>GUI Software Requirements Specification</td><td></td></tr></table>

## GUIAddText

gtk\_list\_append\_items() function should be used to perform the operation.

GUISetListItemData Associates data with a list box item. gtk\_object\_set\_user\_data() function should be used to perform the operation. Time needed for porting: 1 hour.

## GUIGetListItemData

## GUIAddTextList

Adds a text list item to the list using a callback.   
gtk\_list\_append\_items() function should be used to perform the operation.   
Time needed for porting: 4 hours.

## GUIInsertText

Inserts a text item to a given location in list.

gtk\_list\_insert\_items() function should be used to perform the operation.

## GUIClearList

Removes all items from the list.   
gtk\_list\_clear\_items() function should be used to perform the operation.   
Time needed for porting: 2 hours.

## GUIDeleteItem

Deletes an item from the list.

gtk\_list\_clear\_items() function should be used to perform the operation.

GUIGetListSize Returns the number of items in the list. The number of items in the list can be obtained via g\_list\_length() applied to the result of gtk\_container\_get\_children() function. Time needed for porting: 2 hours.

<table><tr><td>Open Watcom Linux Port</td><td>Page 52 of 54</td></tr><tr><td>GUI Software Requirements Specification</td><td></td></tr></table>

## GUIGetCurrSelect

Gets the position of the current selection.

To get the list of the selected items selection field of the GtkList should be used. Then, it is needed to compare all the elements in the list with the selected item, and find out number of the selected item.

Time needed for porting: 3 hours.

## GUISetCurrSelect

Sets current selection by position.

gtk\_list\_select\_item() function should be used to perform the operation.

Time needed for porting: 2 hours.

## GUIGetListItem

Gets the text of a list item by position.

g\_list\_nth() applied to the result of gtk\_container\_get\_children() function should be used to perform the operation.

Time needed for porting: 3 hours.

## GUILimitEditText

Sets the maximum allowed length of the contents of the combo box.

gtk\_entry\_set\_max\_length() applied to entry field of the GtkCombo should be used to perform the operation.

Time needed for porting: 3 hours.

## GUIInsertMenuByID

Inserts a sub menu into the menu before the item with the given ID.

The function should insert an entry in the GtkList widget using g\_list\_insert\_before() function.

Time needed for porting: 3 hours.

## Summary

33 hours is needed for porting activity and, additionally, it is needed approximately 33 hours for testing and tuning. This step requires about 66 hours.

## 26. Radio button and check box functions

GUIIsChecked()

GUISetChecked()

## GUIIsChecked

Finds out if button is checked or not.

gtk\_toggle\_button\_get\_active() should be used to perform the operation.

Time needed for porting: 2 hours.

## GUISetChecked

Sets button as checked or not.

SciTech Software, Inc.

<table><tr><td>Open Watcom Linux Port</td><td>Page 53 of 54</td></tr><tr><td>GUI Software Requirements Specification</td><td></td></tr></table>

gtk\_toggle\_button\_set\_active() should be used to perform the operation.

Time needed for porting: 2 hours.

## Summary

4 hours are needed for porting activity and, additionally, 6 hours are required for testing and tuning. This step requires about 10 hours.

## 27. F1 key hook functions

GUIHookF1()

GUIUnHookF1()

## GUIHookF1

Sets the hook for F1 key pressing event.

Required functionality can be achieved by using gtk\_key\_snooper\_install() function.

Time needed for porting: 4 hours.

## GUIUnHookF1

Removes the hook for F1 key pressing event.

Required functionality can be achieved by using gtk\_key\_snooper\_install() function.

Time needed for porting: 1 hour.

## Summary

5 hours are needed for porting activity and, additionally, 4 hours are needed for testing and tuning. This step requires about 9 hours.

## 28. Other functions.

GUISpawnStart()

GUISpawnEnd()

GUICharLen()

First two does nothing in the GUI version. The third function returns length of a specified character in a char places. In this case, this function should always return 1.

## 29. Type definitions

Here is the basic list of definitions that need to be defined in the GTK port. The definitions of this list was determined on investigation stage, however programmer that will be porting the library will be able determine all necessary type definitions more sharply. Time required – 16 hours.

WPI\_TEXTMETRIC – PangoFontMetrics   
HBRUSH -- GtkRcStyle\*   
HWND -- GtkWindow\*   
WM\_CLOSE -- "close"   
WM\_RESIZE -- "size-request"   
WPI\_COLOUR -- GdkColor\*

SciTech Software, Inc.

<table><tr><td>Open Watcom Linux Port</td><td>Page 54 of 54</td></tr><tr><td>GUI Software Requirements Specification</td><td></td></tr></table>

## 30. Functions that are never used in the current code

## GUIDropDown

Drops down or raise dropped down list box.

## GUIScrollCaret

Scrolls the caret.

## GUISetTopIndex

Sets the index of item at the top of list.

## GUIGetTopIndex

Gets the index of item at the top of list.

## GUISetHorizontalExtent

Sets the width of the widest list box item.

## GUIActivateNC

Activates non client MDI window.