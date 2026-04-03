"""
Inventory of symbols exposed by uProcess_x64.pyd (LabSmith uProcess Python binding).

Source: runtime introspection via dir() on uProcess_x64.CSyringe, C4VM, CEIB.
This is not official vendor documentation; names match the embedded .NET API surface.

Use this module to see what *could* be wrapped next beyond CSyringe / CManifold / LabsmithBoard.
"""

from __future__ import annotations

# Populated from: dir(uProcess_x64.uProcess_x64.CSyringe) etc. (see repo history / re-run introspection).
CEIB_METHODS = (
    "ChADefault ChAStatus ChBDefault ChBStatus ChCDefault ChCStatus ChDDefault ChDStatus "
    "CloseConnection CmdCreateDeviceList CmdGetChannelDefaults CmdGetName CmdGetStatus "
    "CmdPing CmdSetChannelDefaults CmdSetName GetComPort GetName InitConnection "
    "New4AM New4PM New4VM NewEP01 NewSPS01 ObsoleteDevices PurgeOldDevices"
).split()

CSYRINGE_METHODS = (
    "CmdAutoCal CmdClearStall CmdGetDiameter CmdGetName CmdGetStatus CmdGetVolume "
    "CmdMicrostep CmdMovePerChannel CmdMoveToPosition CmdMoveToVolume CmdReset "
    "CmdSetDevAddr CmdSetDiameter CmdSetFlowrate CmdSetName CmdSetPower CmdSetStepDirection "
    "CmdShowDevice CmdStop GetAddress GetLastCount GetLastPosition GetLastVolume "
    "GetMaxFlowrate GetMaxVolume GetMinFlowrate GetName GetVolumeFromPos "
    "IsCalibrating IsDone IsFullSpeed IsMoving IsMovingIn IsMovingOut IsOnline IsRunning "
    "IsStalled IsStartup LastCount LastPos LastState LastVolume"
).split()

# CmdSetValves(v1..v4): 0=no change, 1=position A, 2=closed, 3=position B (per __doc__).
C4VM_METHODS = (
    "AutotuneThresh CmdGetAllCounters CmdGetAutoParameters CmdGetCalTweaks CmdGetCalibration "
    "CmdGetCounter CmdGetLoaddName CmdGetMotionSettings CmdGetName CmdGetStatus "
    "CmdMovePerChannel CmdRecallValveStates CmdReset CmdSaveAllCounters CmdSaveAsBootState "
    "CmdSaveCounter CmdSaveValveStates CmdScanValves CmdSelect CmdSetAutoParameters "
    "CmdSetCalibration CmdSetCounter CmdSetDevAddr CmdSetLoadName CmdSetMotionSettings "
    "CmdSetName CmdSetPos CmdSetValveMotion CmdSetValves CmdShowDevice CmdStop CountThresh "
    "GetAddress GetCalTweaks GetName GetPos GetSel GetSuggestedActions GetValve GetValveStatus "
    "IsDone IsMoving IsOnline IsStuck ParseMoving ParsePosition ParseSelection ParseStuck "
    "V1Missing V1Status V2Missing V2Status V3Missing V3Status V4Missing V4Status"
).split()
