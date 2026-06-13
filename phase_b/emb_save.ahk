#Requires AutoHotkey v2.0
#SingleInstance Force
;==============================================================================
; emb_save.ahk  —  Phase B of the photo→.EMB pipeline (Windows, licensed ES).
;
; Drives Wilcom EmbroideryStudio through the GUI to turn a Phase-A VP3 into a
; native, editable .EMB:
;     open VP3  ->  recognise objects/outlines  ->  Save As .emb  ->  leave open
;
; It only presses keys you could press yourself — it does not decrypt, bypass
; the dongle, or reverse-engineer anything. Needs an unlocked, logged-in desktop
; with ES running at the SAME elevation as this script.
;
; RUN:
;   double-click this file        -> a picker asks for the VP3, OR
;   "...\AutoHotkey64.exe" emb_save.ahk "C:\path\to\NAME_pro.vp3"
;
; FIRST RUN: keep CONFIG.safeMode := true. The script PAUSES before every
; irreversible step so you can watch it, do anything it can't, and confirm. Once
; the keystrokes below match your ES version, set safeMode := false to run hands
; -off. Every action is appended to emb_save.log next to this script.
;==============================================================================

;=========================== CONFIG — EDIT FOR YOUR MACHINE ===================
; The version-specific bits live here. Confirm each against your ES build during
; the first supervised run; the defaults are the common cases, not guarantees.
CONFIG := {
    ; Main-window title (substring match). Find the exact text in your title bar.
    ; Wilcom EmbroideryStudio -> "EmbroideryStudio";  Hatch -> "Hatch Embroidery".
    esTitle:    "Hatch Embroidery",

    ; Optional: full path to the app exe, to auto-launch if it isn't open.
    ; Leave "" to require the app already running (recommended / safest).
    esExe:      "",

    ; Output: "" = write the .emb next to the source VP3, same base name.
    outDir:     "",

    ; HATCH recognises stitches into objects AT OPEN, via the Open dialog's
    ; "Options" button -> "Convert stitches into object shapes". That checkbox
    ; can't be ticked reliably blind, so on open the script pauses for you to do
    ; it (in safeMode). So there is no separate post-open recognise step here.
    recognize:  false,

    ; Supervised mode: confirm before each irreversible step. Keep true early.
    safeMode:   true,

    ;--- keystrokes / menus — VERIFY THESE against your build -----------------
    openKeys:   "^o",       ; File > Open design                (Ctrl+O, standard)
    saveAsKeys: "^s",       ; Hatch: Ctrl+S saves native .EMB (Save As for a new
                            ; design). EmbroideryStudio: try "{F12}" or "^+s".

    ; (EmbroideryStudio only) menu accelerators for Stitch > Recognize
    ; Objects/Outlines, e.g. ["!s","r"]. Unused in Hatch (recognise-on-open).
    recognizeMenu: [],

    ;--- dialog titles (substring) --------------------------------------------
    openDlgTitle:   "Open",
    saveDlgTitle:   "Save",   ; Hatch may title it "Save As" / "Save design as"

    ;--- timeouts (seconds) ---------------------------------------------------
    tWindow:   30,    ; wait for ES main window
    tDialog:   15,    ; wait for a file dialog
    tProcess:  90,    ; wait for recognition / save to finish
    settle:    600    ; ms pause between steps (let the UI catch up)
}
;==============================================================================

SetTitleMatchMode 2
SetKeyDelay 40, 40
LogFile := A_ScriptDir "\emb_save.log"

Main()

Main() {
    global CONFIG
    Log("==== emb_save start ====")

    vp3 := GetVp3Path()
    if (vp3 = "")
        Die("No VP3 selected.")
    if !FileExist(vp3)
        Die("VP3 not found: " vp3)
    emb := EmbOutputPath(vp3)
    Log("VP3 : " vp3)
    Log("EMB : " emb)

    if FileExist(emb)
        if !Confirm("Output already exists and will be overwritten:`n" emb "`n`nContinue?")
            Die("Cancelled by user (existing .emb).")

    EnsureES()
    FocusES()

    ; --- open the VP3 (and recognise objects, Hatch-style) ------------------
    Step("Open the VP3 — converting stitches into editable objects")
    Send CONFIG.openKeys
    if !WinWaitActive(CONFIG.openDlgTitle, , CONFIG.tDialog)
        Die("Open dialog never appeared (openKeys/openDlgTitle wrong?).")
    Sleep CONFIG.settle
    if CONFIG.safeMode {
        ; Hatch's "Convert stitches into object shapes" lives behind the Open
        ; dialog's Options button and can't be ticked reliably blind — you drive
        ; this one step. (The path is already on the clipboard for you.)
        A_Clipboard := vp3
        MsgBox("In Hatch's Open dialog:`n"
             . " 1) browse to / paste this VP3:`n      " vp3 "`n"
             . " 2) click 'Options' and tick 'Convert stitches into object"
             . " shapes'`n"
             . " 3) click Open.`n`nClick OK here once the design is open.",
             "Open + convert to objects", "OK Icon!")
    } else {
        ; Unattended: rely on Hatch's default (machine files convert on open).
        SendText vp3
        Send "{Enter}"
        Sleep CONFIG.settle
        HandlePossiblePrompt("Open Options / import prompt")
    }
    if !WinWaitActive(CONFIG.esTitle, , CONFIG.tWindow)
        Die("Main window not active after open.")
    Log("Opened VP3 (objects).")

    ; --- recognise objects/outlines ----------------------------------------
    if CONFIG.recognize {
        Step("Recognise objects/outlines (so Reshape / Break Apart work)")
        if CONFIG.recognizeMenu.Length = 0 {
            ; No menu path configured — ask the human to do it, then continue.
            MsgBox("Recognise objects/outlines now in ES (Stitch > Recognize"
                 . " Objects/Outlines), then click OK to continue.",
                 "Manual step", "OK Icon!")
        } else {
            FocusES()
            for key in CONFIG.recognizeMenu {
                Send key
                Sleep 250
            }
            Sleep CONFIG.tProcess * 1000 // 6   ; give it a moment to chew
        }
        Log("Recognition step done.")
    }

    ; --- Save As .emb -------------------------------------------------------
    Step("Save As native .emb")
    FocusES()
    Send CONFIG.saveAsKeys
    if !WinWaitActive(CONFIG.saveDlgTitle, , CONFIG.tDialog)
        Die("Save As dialog never appeared (saveAsKeys/saveDlgTitle wrong?).")
    Sleep CONFIG.settle
    ; Type the full path. ES picks the format from the .emb extension; if your
    ; build needs an explicit "Save as type", select it manually in safeMode.
    SendText emb
    Send "{Enter}"
    Sleep CONFIG.settle
    HandlePossiblePrompt("overwrite / save options prompt")

    ; --- verify the file landed --------------------------------------------
    if !WaitForFile(emb, CONFIG.tProcess)
        Die("Did not find the saved .emb within timeout: " emb)
    Log("Saved EMB: " emb " (" FileGetSize(emb) " bytes)")

    Log("==== emb_save done — design left open for QC ====")
    MsgBox("Done.`n`nSaved: " emb "`n`nThe design is left open in ES — QC it:"
         . " try Break Apart / Reshape, check stitch types and TrueView.",
         "emb_save", "OK Iconi")
}

;--------------------------------- helpers -----------------------------------
GetVp3Path() {
    global CONFIG
    if A_Args.Length >= 1
        return A_Args[1]
    return FileSelect(1, , "Select the Phase-A VP3 to convert", "Embroidery (*.vp3)")
}

EmbOutputPath(vp3) {
    global CONFIG
    SplitPath vp3, &name, &dir, , &base
    ; strip a trailing "_pro" so NAME_pro.vp3 -> NAME.emb
    base := RegExReplace(base, "_pro$", "")
    outDir := (CONFIG.outDir != "") ? CONFIG.outDir : dir
    return outDir "\" base ".emb"
}

EnsureES() {
    global CONFIG
    if WinExist(CONFIG.esTitle) {
        Log("ES already running.")
        return
    }
    if (CONFIG.esExe = "")
        Die("ES is not running and CONFIG.esExe is empty. Launch ES first.")
    if !FileExist(CONFIG.esExe)
        Die("CONFIG.esExe not found: " CONFIG.esExe)
    Log("Launching ES: " CONFIG.esExe)
    Run CONFIG.esExe
    if !WinWait(CONFIG.esTitle, , CONFIG.tWindow)
        Die("ES window did not appear within " CONFIG.tWindow "s.")
}

FocusES() {
    global CONFIG
    if !WinExist(CONFIG.esTitle)
        Die("ES window vanished.")
    WinActivate CONFIG.esTitle
    if !WinWaitActive(CONFIG.esTitle, , 5)
        Die("Could not focus ES.")
    Sleep CONFIG.settle
}

; Pause before an irreversible step in safe mode; always log it.
Step(desc) {
    global CONFIG
    Log("STEP: " desc)
    if CONFIG.safeMode
        if !Confirm("Next step:`n`n" desc "`n`nProceed?")
            Die("Cancelled by user at: " desc)
}

Confirm(msg) {
    res := MsgBox(msg, "emb_save — confirm", "YesNo Icon?")
    return (res = "Yes")
}

; Best-effort: if a modal popped up, let the human deal with it in safe mode,
; otherwise press Enter to accept the default.
HandlePossiblePrompt(what) {
    global CONFIG
    Sleep CONFIG.settle
    if CONFIG.safeMode {
        MsgBox("If a dialog appeared (" what "), set it as needed, then click OK."
             , "Check for a dialog", "OK Icon!")
        return
    }
    Send "{Enter}"
}

WaitForFile(path, seconds) {
    deadline := A_TickCount + seconds * 1000
    while (A_TickCount < deadline) {
        if FileExist(path) && FileGetSize(path) > 0
            return true
        Sleep 500
    }
    return false
}

Log(msg) {
    global LogFile
    ts := FormatTime(A_Now, "yyyy-MM-dd HH:mm:ss")
    try FileAppend(ts "  " msg "`n", LogFile)
    OutputDebug(msg)
}

Die(msg) {
    Log("FATAL: " msg)
    MsgBox(msg, "emb_save — stopped", "OK IconX")
    ExitApp 1
}
