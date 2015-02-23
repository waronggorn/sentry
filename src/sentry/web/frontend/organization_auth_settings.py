from __future__ import absolute_import

from django.core.urlresolvers import reverse

from sentry.auth import manager
from sentry.auth.helper import AuthHelper
from sentry.models import AuthProvider, OrganizationMemberType
from sentry.utils.http import absolute_uri
from sentry.web.frontend.base import OrganizationView


class OrganizationAuthSettingsView(OrganizationView):
    required_access = OrganizationMemberType.OWNER

    def handle_existing_provider(self, request, organization, auth_provider):
        # TODO(dcramer): providers need to be able to extend this page. There
        # should always be a disable + login info blurb but each provider may
        # want to add additional behaviors
        if request.method == 'POST':
            op = request.POST.get('op')
            if op == 'disable':
                auth_provider.delete()

                next_uri = reverse('sentry-organization-auth-settings',
                                   args=[organization.slug])
                return self.redirect(next_uri)

        provider = auth_provider.get_provider()

        context = {
            'login_url': absolute_uri(reverse('sentry-organization-home', args=[organization.slug])),
            'auth_provider': auth_provider,
            'provider_name': provider.name,
        }

        return self.respond('sentry/organization-auth-provider-settings.html', context)

    def handle_provider_setup(self, request, organization, provider_key):
        helper = AuthHelper(
            request=request,
            organization=organization,
            provider_key=provider_key,
            flow=AuthHelper.FLOW_SETUP_PROVIDER,
        )
        helper.init_pipeline()
        return helper.next_step()

    def handle(self, request, organization):
        try:
            auth_provider = AuthProvider.objects.get(
                organization=organization,
            )
        except AuthProvider.DoesNotExist:
            pass
        else:
            return self.handle_existing_provider(
                request=request,
                organization=organization,
                auth_provider=auth_provider,
            )

        if request.method == 'POST':
            provider_key = request.POST.get('provider')
            if not manager.exists(provider_key):
                raise ValueError('Provider not found: {}'.format(provider_key))

            # render first time setup view
            return self.handle_provider_setup(request, organization, provider_key)

        context = {
            'provider_list': [(k, v.name) for k, v in manager],
        }

        return self.respond('sentry/organization-auth-settings.html', context)
