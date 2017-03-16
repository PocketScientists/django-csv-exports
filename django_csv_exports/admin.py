from builtins import str as text

import django
import unicodecsv as csv
from django.conf import settings
from django.contrib import admin
from django.http import HttpResponse, HttpResponseForbidden
from django.utils.translation import ugettext_lazy as _


SHORT_DESCRIPTION = _('Export selected object(s) as CSV file')


def export_as_csv(admin_model, request, queryset):
    """
    Generic csv export admin action.
    based on http://djangosnippets.org/snippets/1697/
    """
    # everyone has perms to export as csv unless explicitly defined
    if getattr(settings, 'DJANGO_EXPORTS_REQUIRE_PERM', False):
        codename = '%s_%s' % ('csv', admin_model.opts.object_name.lower())
        return request.user.has_perm("%s.%s" % (admin_model.opts.app_label, codename))
    else:
        has_csv_permission = admin_model.has_csv_permission(request) \
            if (hasattr(admin_model, 'has_csv_permission') and callable(getattr(admin_model, 'has_csv_permission'))) \
            else True
    if has_csv_permission:
        opts = admin_model.model._meta
        if getattr(admin_model, 'csv_fields', None):
            field_names = admin_model.csv_fields
        else:
            field_names = [field.name for field in opts.fields]
            field_names.sort()

        if django.VERSION[0] == 1 and django.VERSION[1] <= 5:
            response = HttpResponse(mimetype='text/csv')
        else:
            response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename=%s.csv' % text(opts).replace('.', '_')

        writer = csv.writer(response)
        writer.writerow(list(field_names))
        for obj in queryset:
            writer.writerow([text(getattr(obj, field)).encode("utf-8", "replace") for field in field_names])
        return response
    return HttpResponseForbidden()
export_as_csv.short_description = SHORT_DESCRIPTION


class CSVExportAdminMixin(object):
    def get_actions(self, request):
        actions = super(CSVExportAdminMixin, self).get_actions(request)
        if self.has_csv_permission(request):
            actions['export_as_csv'] = (
                export_as_csv,
                'export_as_csv',
                SHORT_DESCRIPTION
            )
        return actions

    def has_csv_permission(self, request, obj=None):
        """
        Returns True if the given request has permission to add an object.
        Can be overridden by the user in subclasses. By default, we assume
        all staff users can use this action unless `DJANGO_EXPORTS_REQUIRE_PERM`
        is set to True in your django settings.
        """
        if getattr(settings, 'DJANGO_EXPORTS_REQUIRE_PERM', False):
            codename = '%s_%s' % ('csv', self.opts.object_name.lower())
            return request.user.has_perm("%s.%s" % (self.opts.app_label, codename))
        return True


class CSVExportAdmin(CSVExportAdminMixin, admin.ModelAdmin):
    pass


# register global action
if getattr(settings, 'DJANGO_CSV_GLOBAL_EXPORTS_ENABLED', False):
    admin.site.add_action(export_as_csv)
