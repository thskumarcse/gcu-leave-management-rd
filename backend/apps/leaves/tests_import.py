import tempfile

from django.test import TestCase

from apps.employees.models import Employee
from apps.leaves.import_services import import_emp_leaves
from apps.leaves.models import LeaveApplication, LeaveType

SAMPLE_XML = """<?xml version="1.0"?>
<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet"
 xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet">
 <Worksheet ss:Name="Employee Leave Report">
  <Table>
   <Row>
    <Cell><Data ss:Type="String">Serial No.</Data></Cell>
    <Cell><Data ss:Type="String">Employee ID</Data></Cell>
    <Cell><Data ss:Type="String">Name</Data></Cell>
    <Cell><Data ss:Type="String">Location</Data></Cell>
    <Cell><Data ss:Type="String">Leave Type</Data></Cell>
    <Cell><Data ss:Type="String">Request Date</Data></Cell>
    <Cell><Data ss:Type="String">From Date</Data></Cell>
    <Cell><Data ss:Type="String">To Date</Data></Cell>
    <Cell><Data ss:Type="String">Status</Data></Cell>
    <Cell><Data ss:Type="String">Timeline</Data></Cell>
   </Row>
   <Row>
    <Cell><Data ss:Type="String">1</Data></Cell>
    <Cell><Data ss:Type="String">GCU020041</Data></Cell>
    <Cell><Data ss:Type="String">Bhabajit Baruah</Data></Cell>
    <Cell><Data ss:Type="String">GCU</Data></Cell>
    <Cell><Data ss:Type="String">Casual Leave</Data></Cell>
    <Cell><Data ss:Type="String">01/03/2026</Data></Cell>
    <Cell><Data ss:Type="String">10/03/2026</Data></Cell>
    <Cell><Data ss:Type="String">11/03/2026</Data></Cell>
    <Cell><Data ss:Type="String">Approved</Data></Cell>
    <Cell><Data ss:Type="String">View</Data></Cell>
   </Row>
   <Row>
    <Cell><Data ss:Type="String">2</Data></Cell>
    <Cell><Data ss:Type="String">GCU020041</Data></Cell>
    <Cell><Data ss:Type="String">Bhabajit Baruah</Data></Cell>
    <Cell><Data ss:Type="String">GCU</Data></Cell>
    <Cell><Data ss:Type="String">Vacation Leave</Data></Cell>
    <Cell><Data ss:Type="String">09/12/2025</Data></Cell>
    <Cell><Data ss:Type="String">26/12/2025</Data></Cell>
    <Cell><Data ss:Type="String">01/01/2026</Data></Cell>
    <Cell><Data ss:Type="String">Approved</Data></Cell>
    <Cell><Data ss:Type="String">View</Data></Cell>
   </Row>
   <Row>
    <Cell><Data ss:Type="String">3</Data></Cell>
    <Cell><Data ss:Type="String">MISSING99</Data></Cell>
    <Cell><Data ss:Type="String">Unknown</Data></Cell>
    <Cell><Data ss:Type="String">GCU</Data></Cell>
    <Cell><Data ss:Type="String">Casual Leave</Data></Cell>
    <Cell><Data ss:Type="String">01/03/2026</Data></Cell>
    <Cell><Data ss:Type="String">02/03/2026</Data></Cell>
    <Cell><Data ss:Type="String">02/03/2026</Data></Cell>
    <Cell><Data ss:Type="String">Approved</Data></Cell>
    <Cell><Data ss:Type="String">View</Data></Cell>
   </Row>
   <Row>
    <Cell><Data ss:Type="String">4</Data></Cell>
    <Cell><Data ss:Type="String">GCU020041</Data></Cell>
    <Cell><Data ss:Type="String">Bhabajit Baruah</Data></Cell>
    <Cell><Data ss:Type="String">GCU</Data></Cell>
    <Cell><Data ss:Type="String">Duty Leave assigned by the University</Data></Cell>
    <Cell><Data ss:Type="String">01/04/2026</Data></Cell>
    <Cell><Data ss:Type="String">01/04/2026</Data></Cell>
    <Cell><Data ss:Type="String">01/04/2026</Data></Cell>
    <Cell><Data ss:Type="String">Withdrawn</Data></Cell>
    <Cell><Data ss:Type="String">View</Data></Cell>
   </Row>
  </Table>
 </Worksheet>
</Workbook>
"""


def write_xml(content=SAMPLE_XML):
    tmp = tempfile.NamedTemporaryFile(
        mode='w', suffix='.xls', delete=False, encoding='utf-8'
    )
    tmp.write(content)
    tmp.close()
    return tmp.name


class ImportEmpLeavesTests(TestCase):
    def setUp(self):
        Employee.objects.create(
            emp_id='GCU020041',
            name='Bhabajit Baruah',
            designation='Assistant Professor',
            designation_type=Employee.DesignationType.FACULTY,
            department='School Of Engineering and Technology',
            sub_department='Department of Mechanical Engineering',
            email='bhabajit_me@gcuniversity.ac.in',
            status=Employee.Status.ACTIVE,
        )

    def test_imports_known_rows_and_skips_unknown_employee(self):
        report = import_emp_leaves(write_xml(), route_pending=False)
        self.assertEqual(report.imported, 3)
        self.assertEqual(report.skipped_count, 1)
        self.assertEqual(LeaveApplication.objects.count(), 3)
        casual = LeaveApplication.objects.get(leave_type__code='CL')
        self.assertEqual(casual.status, LeaveApplication.Status.APPROVED)
        self.assertEqual(casual.days, 2)
        self.assertEqual(casual.source, LeaveApplication.Source.IMPORTED)
        self.assertEqual(casual.requested_on.isoformat(), '2026-03-01')
        self.assertTrue(LeaveType.objects.filter(code='VL').exists())
        withdrawn = LeaveApplication.objects.get(leave_type__code='DL')
        self.assertEqual(withdrawn.status, LeaveApplication.Status.CANCELLED)

    def test_reimport_does_not_duplicate(self):
        path = write_xml()
        import_emp_leaves(path, route_pending=False)
        report = import_emp_leaves(path, route_pending=False)
        self.assertEqual(report.imported, 0)
        self.assertEqual(report.updated, 3)
        self.assertEqual(LeaveApplication.objects.count(), 3)
