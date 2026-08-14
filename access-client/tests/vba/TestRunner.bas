Attribute VB_Name = "TestRunner"
Option Compare Database
Option Explicit

Public Function Test_RunAll() As String
    Test_RunAll = "{""passed"":0,""failed"":0,""tests"":[]}"
End Function

Public Function Test_Bootstrap() As Boolean
    Test_Bootstrap = True
End Function
