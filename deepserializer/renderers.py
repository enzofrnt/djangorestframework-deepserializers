from rest_framework.renderers import BrowsableAPIRenderer

class DeepBrowsableAPIRenderer(BrowsableAPIRenderer):
    """
    This renderer is used to render the browsable API for the EventStream.
    """

    def get_context(self, data, accepted_media_type, renderer_context):
        tkt = super().get_context(data, accepted_media_type, renderer_context)
        print(tkt)
        print(tkt.get("post_form"))  # Use .get() to avoid KeyError in case 'post_form' does not exist
        return tkt
    # template = 'djangorestframework_deepserializer/deep-browsable-api.html'

    # def get_context(self, data, accepted_media_type, renderer_context):
    #     context = super().get_context(data, accepted_media_type, renderer_context)
    #     context['channels'] = data.get('channels', 'Here is no selected channels. Please check documentation to select channels or error.')
    #     context['messages_types'] = data.get('messages_types', 'Here is no selected messages types. Please check documentation to select messages types or error.')
    #     context['error'] = data.get('error')
    #     return context