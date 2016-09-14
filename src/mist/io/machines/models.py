"""Machine entity model."""
import json
import uuid
import mongoengine as me

import mist.core.tag.models
from mist.io.clouds.models import Cloud
from mist.core.keypair.models import Keypair
from mist.io.machines.controllers import MachineController


class Actions(me.EmbeddedDocument):
    start = me.BooleanField()
    stop = me.BooleanField()
    reboot = me.BooleanField()
    destroy = me.BooleanField()
    resize = me.BooleanField()
    rename = me.BooleanField()
    tag = me.BooleanField()
    resume = me.BooleanField()
    suspend = me.BooleanField()
    undefine = me.BooleanField()


# # TODO move these when keys port is completed
from mist.core.cloud.models import KeyAssociation, InstallationStatus

class Monitoring(me.EmbeddedDocument):
    # Most of these will change with the new UI.
    hasmonitoring = me.BooleanField()
    monitor_server = me.StringField()
    collectd_password = me.StringField()
    metrics = me.ListField()  # list of metric_id's
    installation_status = me.EmbeddedDocumentField(InstallationStatus)


class Cost(me.EmbeddedDocument):
    hourly = me.FloatField()
    monthly = me.FloatField()


class Machine(me.Document):
    """The basic machine model"""

    id = me.StringField(primary_key=True, default=lambda: uuid.uuid4().hex)

    cloud = me.ReferenceField(Cloud, required=True)
    name = me.StringField()

    # Info gathered mostly by libcloud (or in some cases user input).
    # Be more specific about what this is.
    # We should perhaps come up with a better name.
    machine_id = me.StringField(required=True, unique_with="cloud")
    hostname = me.StringField()  # Rename to host or hostname
    public_ips = me.ListField()
    private_ips = me.ListField()
    ssh_port = me.IntField(default=22)
    os_type = me.StringField(default='unix', choices=('unix', 'windows'))
    rdp_port = me.IntField(default=3389)

    actions = me.EmbeddedDocumentField(Actions, default=lambda: Actions())
    extra = me.DictField()
    cost = me.EmbeddedDocumentField(Cost, default=lambda: Cost())
    image_id = me.StringField()
    size = me.StringField()
    state = me.StringField()  # TODO choices maybe
    # TODO better DictField and in as_dict() make it list for js
    tags = me.ListField()

    # We should think this through a bit.
    key_associations = me.EmbeddedDocumentListField(KeyAssociation)

    last_seen = me.DateTimeField()
    missing_since = me.DateTimeField()
    created = me.DateTimeField()

    monitoring = me.EmbeddedDocumentField(Monitoring,
                                          default=lambda: Monitoring())

    meta = {
        'collection': 'machines',
    }

    def __init__(self, *args, **kwargs):
        super(Machine, self).__init__(*args, **kwargs)
        self.ctl = MachineController(self)

    # Should this be a field? Should it be a @property? Or should it not exist?
    @property
    def owner(self):
        return self.cloud.owner

    def delete(self):
        super(Machine, self).delete()
        mist.core.tag.models.Tag.objects(resource=self).delete()

    def as_dict(self):
        # Return a dict as it will be returned to the API
        # TODO tags as a list return for the ui
        return {
            'id': self.id,
            'hostname': self.hostname,
            'public_ips': self.public_ips,
            'private_ips': self.private_ips,
            'name': self.name,
            'ssh_port': self.ssh_port,
            'os_type': self.os_type,
            'rdp_port': self.rdp_port,
            'machine_id': self.machine_id,
            'actions': [('%s:' % (action), self.actions[action])
                        for action in self.actions], # TODO check this
            'extra': self.extra,
            'cost_per_hour': self.cost.hourly,
            'cost_per_month': self.cost.monthly,
            'image_id': self.image_id,
            'size': self.size,
            'state': self.state,
            'tags': self.tags,
            'hasMonitoring': self.monitoring.hasmonitoring,
            'monitor_server': self.monitoring.monitor_server,
            'collectd_password': self.monitoring.collectd_password,
            'installation_status': self.monitoring.installation_status,
            'key_associations': self.key_associations,
            'cloud': self.cloud.id,
            'last_seen': str(self.last_seen or ''),
            'missing_since': str(self.missing_since or ''),
            'created': str(self.created or '')
        }

    def as_dict_old(self):
        # Return a dict as it was previously being returned by list_machines

        # This is need to be consistent with the previous situation
        self.extra.update({'created': str(self.created or ''),
                           'cost_per_month': '%.2f' % self.cost.monthly,
                           'cost_per_hour': '%.2f' % self.cost.hourly})
        return {
            'id': self.machine_id,
            'uuid': self.id,
            '_id': self.id,
            'name': self.name,
            'dns_name': self.hostname,
            'public_ips': self.public_ips,
            'private_ips': self.private_ips,
            'ssh_port': self.ssh_port,
            'os_type': self.os_type,
            'imageId': self.image_id,
            'remote_desktop_port': self.rdp_port,
            'hasMonitoring': self.monitoring.hasmonitoring,
            'monitor_server': self.monitoring.monitor_server,
            'collectd_password': self.monitoring.collectd_password,
            'metrics': self.monitoring.metrics,
            'installation_status': self.monitoring.installation_status,
            'key_associations': self.key_associations,
            'cloud': self.cloud.id,
            'last_seen': str(self.last_seen or ''),
            'missing_since': str(self.missing_since or ''),
            'state': self.state,
            'size': self.size,
            'tags': self.tags,
            'extra': self.extra,
            'can_stop': self.actions.stop,
            'can_start': self.actions.start,
            'can_destroy': self.actions.destroy,
            'can_reboot': self.actions.reboot,
            'can_tag': self.actions.tag,
            'can_undefine': self.actions.undefine,
            'can_rename': self.actions.rename,
            'can_suspend': self.actions.suspend,
            'can_resume': self.actions.resume
        }

    def __str__(self):
        return 'Machine %s (%s) in %s' % (self.name, self.id, self.cloud)
