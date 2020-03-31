from sortedcontainers import SortedDict, SortedSet


class InputMessages:
    def __init__(self):
        self.predecessors = {}
        self.times_set = SortedSet()

    def set_connections(self, connection_graphs, sid):
        for graph in connection_graphs:
            for src_sid in graph.predecessors(sid):
                connections = graph[src_sid][sid]['messageflows']
                for src_eid, dest_eid, messages in connections:
                    for src_msg, dest_msg in messages:
                        src_dict = self.predecessors.setdefault((src_sid, src_eid, src_msg), {
                            'input_queue': SortedDict(), 'output_map': set()})
                        src_dict['output_map'].add((dest_eid, dest_msg))

    def add(self, message_time, src_sid, src_eid, src_msg, value):
        self.predecessors[(src_sid, src_eid, src_msg)]['input_queue'][message_time] = value
        self.times_set.add(message_time)

    def add_empty_time(self, message_time):
        self.times_set.add(message_time)

    def get_messages(self, step):
        messages = {}
        for src_tuple, src_dict in self.predecessors.items():
            message_queue = src_dict['input_queue']
            actual_messages = list(message_queue.irange(maximum=step))
            # TODO: We use the full message id here, as different messages from
            #  one source entity could be connected to the same message of the
            #  destination entity. Are there use cases for this?
            src_msg_full_id = '.'.join(map(str, src_tuple))  # TODO: Replace by FULL_ID?
            if actual_messages:
                message_list = []
                for _ in actual_messages:
                    _, message = message_queue.popitem(0)
                    message_list.append(message)

                for eid, attr in src_dict['output_map']:
                    messages.setdefault(eid, {}).setdefault(attr, {})[src_msg_full_id] = message_list

        for _ in list(self.times_set.irange(maximum=step)):
            self.times_set.pop(0)

        return messages

    def peek_next_time(self):
        if self.times_set:
            next_time = self.times_set[0]
        else:
            next_time = None

        return next_time

    def __bool__(self):
        return bool(self.times_set)
