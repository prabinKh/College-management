from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib import messages
from student.models import Student, Parent
from home_auth.models import CustomUser
from django.utils import timezone

class StudentViewsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user_model = get_user_model()
        # Create an admin user for authentication
        self.admin_user = self.user_model.objects.create_user(
            username='admin@example.com',
            email='admin@example.com',
            password='adminpass123',
            is_admin=True
        )

    def test_add_10_students(self):
        """Test adding 10 students to the database via the add_student view."""
        self.client.login(username='admin@example.com', password='adminpass123')

        for i in range(10):
            # Simulate POST data for add_student view
            data = {
                'first_name': f'Student{i}',
                'last_name': f'Last{i}',
                'student_email': f'student{i}@example.com',
                'gender': 'Male',
                'date_of_birth': '2000-01-01',
                'student_class': '10',
                'religion': 'Unknown',
                'joining_date': '2025-08-01',
                'mobile_number': f'123456789{i}',
                'admission_number': f'ADM{i:04d}',
                'section': 'A',
                'father_name': f'Father{i}',
                'father_occupation': 'Engineer',
                'father_mobile': f'987654321{i}',
                'father_email': f'father{i}@example.com',
                'mother_name': f'Mother{i}',
                'mother_occupation': 'Teacher',
                'mother_mobile': f'876543210{i}',
                'mother_email': f'mother{i}@example.com',
                'present_address': f'123 Street {i}',
                'permanent_address': f'456 Avenue {i}'
            }

            # Post to add_student view
            response = self.client.post(reverse('students:add_student'), data, follow=True)
            self.assertEqual(response.status_code, 200)  # Follow redirects to final page
            self.assertRedirects(response, reverse('students:student_list'))

            # Verify success message
            messages_list = list(messages.get_messages(response.wsgi_request))
            self.assertTrue(any(msg.message == 'Student added successfully' for msg in messages_list), 
                           f"Expected 'Student added successfully' in messages, got: {[str(m) for m in messages_list]}")

            # Verify Student and Parent creation
            student = Student.objects.get(email=f'student{i}@example.com')
            self.assertEqual(student.user.email, f'student{i}@example.com')
            self.assertEqual(student.first_name, f'Student{i}')
            self.assertEqual(student.last_name, f'Last{i}')
            self.assertEqual(student.admission_number, f'ADM{i:04d}')

            parent = Parent.objects.get(student=student)
            self.assertEqual(parent.father_name, f'Father{i}')
            self.assertEqual(parent.mother_name, f'Mother{i}')

        # Verify 10 CustomUsers, Students, and Parents were created
        self.assertEqual(self.user_model.objects.filter(is_student=True).count(), 10)
        self.assertEqual(Student.objects.count(), 10)
        self.assertEqual(Parent.objects.count(), 10)