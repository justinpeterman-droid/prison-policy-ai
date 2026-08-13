Attribute VB_Name = "TestAssert"
Option Compare Database
Option Explicit

Public Sub AreEqual(ByVal Expected As Variant, ByVal Actual As Variant, ByVal Context As String)
    If Expected <> Actual Then
        TestAssert.Fail Context & ": expected [" & CStr(Expected) & "] but got [" & CStr(Actual) & "]"
    End If
End Sub

Public Sub IsTrue(ByVal Condition As Boolean, ByVal Context As String)
    If Not Condition Then
        TestAssert.Fail Context & ": expected True"
    End If
End Sub

Public Sub Fail(ByVal Message As String)
    Err.Raise vbObjectError + 512, "TestAssert", Message
End Sub
