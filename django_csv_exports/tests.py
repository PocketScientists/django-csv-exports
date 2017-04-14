from django.contrib.admin.sites import AdminSite
from django.db import models
from django.test import TestCase

from django_csv_exports.admin import CSVExportAdmin


class Foo(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return self.name


class CSVExportAdminTests(TestCase):
    def setUp(self):
        self.foo = Foo.objects.create(
            name='the name',
        )
        self.site = AdminSite()

    def test_action_available(self):
        ma = CSVExportAdmin(Foo, self.site)

        import ipdb;ipdb.set_trace()
        self.assertEqual(1 + 1, 2)
