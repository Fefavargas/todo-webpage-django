from django.test import TestCase
from django.urls import reverse
from .models import Task
from django.utils import timezone
import json


class TaskModelTests(TestCase):
	def test_due_date_nullable(self):
		t = Task.objects.create(title='No due')
		self.assertIsNone(t.due_date)
		# set a date and save
		d = timezone.now().date()
		t.due_date = d
		t.save()
		t2 = Task.objects.get(pk=t.pk)
		self.assertEqual(t2.due_date, d)


class TaskViewTests(TestCase):
	def test_create_task_via_home_post(self):
		# POST to home to create a task with due_date
		url = reverse('home')
		data = {'title': 'buy milk', 'due_date': '2025-12-31'}
		resp = self.client.post(url, data)
		# view redirects back to home after create
		self.assertEqual(resp.status_code, 302)
		self.assertEqual(resp.url, reverse('home'))
		# ensure task exists
		self.assertTrue(Task.objects.filter(title='buy milk').exists())

	def test_create_invalid_submission_no_title(self):
		url = reverse('home')
		# missing title should not create a task but still redirect
		resp = self.client.post(url, {'due_date': '2025-12-31'})
		self.assertEqual(resp.status_code, 302)
		self.assertEqual(Task.objects.count(), 0)

	def test_update_task_post(self):
		t = Task.objects.create(title='old', completed=False)
		url = reverse('update', args=[t.pk])
		data = {'title': 'new title', 'due_date': '2025-11-30', 'completed': 'on'}
		resp = self.client.post(url, data)
		# should redirect back to home
		self.assertEqual(resp.status_code, 302)
		self.assertEqual(resp.url, reverse('home'))
		t.refresh_from_db()
		self.assertEqual(t.title, 'new title')
		# completed checkbox should be processed by the view
		self.assertTrue(t.completed)
		self.assertEqual(str(t.due_date), '2025-11-30')

	def test_update_nonexistent_returns_404(self):
		url = reverse('update', args=[9999])
		resp = self.client.post(url, {'title': 'x'})
		self.assertEqual(resp.status_code, 404)

	def test_toggle_complete_endpoint(self):
		t = Task.objects.create(title='flip me', completed=False)
		url = reverse('toggle', args=[t.pk])
		resp = self.client.post(url, {}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
		self.assertEqual(resp.status_code, 200)
		# JSON response should include completed status
		self.assertIn('application/json', resp['Content-Type'])
		data = json.loads(resp.content)
		self.assertTrue(data.get('ok'))
		self.assertTrue(data.get('completed'))
		t.refresh_from_db()
		self.assertTrue(t.completed)

	def test_toggle_nonexistent_returns_404(self):
		url = reverse('toggle', args=[9999])
		resp = self.client.post(url)
		self.assertEqual(resp.status_code, 404)

	def test_delete_task_post(self):
		t = Task.objects.create(title='to delete')
		url = reverse('delete', args=[t.pk])
		resp = self.client.post(url)
		# should redirect back to home
		self.assertEqual(resp.status_code, 302)
		self.assertEqual(resp.url, reverse('home'))
		# after delete it should not exist
		self.assertFalse(Task.objects.filter(pk=t.pk).exists())

	def test_delete_nonexistent_returns_404(self):
		url = reverse('delete', args=[9999])
		resp = self.client.post(url)
		self.assertEqual(resp.status_code, 404)

	def test_home_renders_template(self):
		url = reverse('home')
		resp = self.client.get(url)
		self.assertEqual(resp.status_code, 200)
		self.assertTemplateUsed(resp, 'home.html')


	class MigrationFilesTests(TestCase):
		def test_initial_migration_creates_task_model(self):
			"""Ensure the app's initial migration defines the Task model.

			This is a static check on the migration files and will catch
			deleted/missing migrations that would cause "no such table" at runtime.
			"""
			from django.db.migrations.loader import MigrationLoader
			from django.db import connections, DEFAULT_DB_ALIAS

			loader = MigrationLoader(connections[DEFAULT_DB_ALIAS])
			disk_migrations = loader.disk_migrations
			key = ("todo", "0001_initial")
			# the migration file should exist on disk
			self.assertIn(key, disk_migrations, msg=f"Migration {key} not found on disk")
			migration = disk_migrations[key]
			# find CreateModel operations and ensure Task is created
			create_models = [op for op in migration.operations if op.__class__.__name__ == 'CreateModel']
			names = [op.name for op in create_models]
			self.assertIn('Task', names, msg='Initial migration does not create Task model')

