!ifndef YUMO_CONTEXT_MENU_INCLUDED
!define YUMO_CONTEXT_MENU_INCLUDED

!define YUMO_CONTEXT_MENU_KEY "Software\Classes\*\shell\YuMoEditor"

!macro yumo.registerContextMenu
    SetRegView 64
    WriteRegStr SHCTX "${YUMO_CONTEXT_MENU_KEY}" "" "以 YuMo Editor 編輯"
    WriteRegStr SHCTX "${YUMO_CONTEXT_MENU_KEY}" "Icon" '$\"$INSTDIR\${PRODUCT_EXECUTABLE}$\",0'
    WriteRegStr SHCTX "${YUMO_CONTEXT_MENU_KEY}" "MultiSelectModel" "Document"
    WriteRegStr SHCTX "${YUMO_CONTEXT_MENU_KEY}\command" "" '$\"$INSTDIR\${PRODUCT_EXECUTABLE}$\" $\"%1$\"'
    System::Call 'shell32::SHChangeNotify(i 0x08000000, i 0, p 0, p 0)'
!macroend

!macro yumo.unregisterContextMenu
    SetRegView 64
    ; An older installation must not remove a newer installation's command.
    ReadRegStr $0 SHCTX "${YUMO_CONTEXT_MENU_KEY}\command" ""
    ${If} $0 == '$\"$INSTDIR\${PRODUCT_EXECUTABLE}$\" $\"%1$\"'
        DeleteRegKey SHCTX "${YUMO_CONTEXT_MENU_KEY}"
        System::Call 'shell32::SHChangeNotify(i 0x08000000, i 0, p 0, p 0)'
    ${EndIf}
!macroend

!endif
