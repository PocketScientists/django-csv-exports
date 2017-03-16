from builtins import str as text

import django
import unicodecsv as csv
from django.conf import settings
from django.contrib import admin
from django.http import HttpResponse, HttpResponseForbidden
from django.utils.translation import ugettext_lazy as _

MODEL_ADMIN_FIELDNAMES = 'csv_fields'
MODEL_ADMIN_FILENAME = 'csv_filename'

SHORT_DESCRIPTION = _('Export selected object(s) as CSV file')

RESPONSE_CONTENT_TYPE = 'text/csv'
RESPONSE_ATTACHMENT = True


def get_value(admin_model, instance, field_name):
    # try getting a value from the instance
    value = getattr(instance, field_name, None)
    # if unsuccessful, try the admin
    if not value:
        value = getattr(admin_model, field_name, None)
    # if we have something, try if it's a callable
    if value and callable(value):
        value = value(instance)
    return text(value)


def get_fieldnames(admin_model):
    # use field names from specific ModelAdmin configuration
    if getattr(admin_model, MODEL_ADMIN_FIELDNAMES, None):
        field_names = admin_model.csv_fields
    else:
        # fallback to Modeladmin.fields
        field_names = [field.name for field in admin_model.model._meta.fields]
        field_names.sort()
    return field_names


def set_content_disposition(response, admin_model, filename=None):
    # default filename is derived from Model._meta
    filename = text(admin_model.model._meta).replace('.', '_') + '.csv'
    # override of filename using csv_filename attribute
    filename = getattr(admin_model, MODEL_ADMIN_FILENAME, filename)
    # attribute can be callable for more dynamic filenames
    if callable(filename):
        filename = filename()

    response['Content-Disposition'] = 'attachment; filename={}'.format(filename)


def get_response(admin_model):
    content_type_name = 'content_type'
    #TODO extended support for 1.5 ended in sept 2014, remove this
    if django.VERSION[0] == 1 and django.VERSION[1] <= 5:
        content_type_name = 'mimetype'

    response = HttpResponse(**{content_type_name: RESPONSE_CONTENT_TYPE})

    # offer content as "file" in response
    if RESPONSE_ATTACHMENT:
        set_content_disposition(response, admin_model)

    return response


def has_csv_permission(admin_model, request):
    # everyone has perms to export as csv unless explicitly defined
    if getattr(settings, 'DJANGO_EXPORTS_REQUIRE_PERM', False):
        codename = '%s_%s' % ('csv', admin_model.opts.object_name.lower())
        return request.user.has_perm("%s.%s" % (admin_model.opts.app_label, codename))
    else:
        return admin_model.has_csv_permission(request) \
            if (hasattr(admin_model, 'has_csv_permission') and callable(getattr(admin_model, 'has_csv_permission'))) \
            else True


def export_as_csv(admin_model, request, queryset):
    """
    Generic csv export admin action.
    originally based on http://djangosnippets.org/snippets/1697/
    """
    if has_csv_permission(admin_model, request):
        field_names = get_fieldnames(admin_model)
        response = get_response(admin_model)

        writer = csv.writer(response, encoding='utf-8')
        writer.writerow(list(field_names))
        for obj in queryset:
            writer.writerow([
                get_value(admin_model, obj, field)
                for field in field_names
            ])
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
