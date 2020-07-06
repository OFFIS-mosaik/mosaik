import heapq as hq


class InputMessages:
    def __init__(self):
        self.output_map = {}
        self.input_queue = []

    def set_connections(self, connection_graphs, sid):
        for graph in connection_graphs:
            for src_sid in graph.predecessors(sid):
                connections = graph[src_sid][sid]['messageflows']
                for src_eid, dest_eid, messages in connections:
                    for src_msg, dest_msg in messages:
                        src_msg_full_id = '.'.join(map(str, (src_sid, src_eid, src_msg)))
                        self.output_map.setdefault(src_msg_full_id, set()).add((dest_eid, dest_msg))

    def add(self, message_time, src_sid, src_eid, src_msg, value):
        src_msg_full_id = '.'.join(map(str, (src_sid, src_eid, src_msg)))
        hq.heappush(self.input_queue, (message_time, src_msg_full_id, value))

    def add_empty_time(self, message_time):
        hq.heappush(self.input_queue, (message_time, '', None))

    def get_messages(self, step):
        messages = {}
        for src_msg_full_id, dest_tuples in self.output_map.items():
            for eid, attr in dest_tuples:
                messages.setdefault(eid, {}).setdefault(attr, {})[
                                                          src_msg_full_id] = []

        while len(self.input_queue) > 0 and self.input_queue[0][0] <= step:
            _, src_msg_full_id, value = hq.heappop(self.input_queue)

            for eid, attr in self.output_map[src_msg_full_id]:
                messages[eid][attr][src_msg_full_id].append(value)

        return messages

    def peek_next_time(self):
        if len(self.input_queue):
            next_time = self.input_queue[0][0]
        else:
            next_time = None

        return next_time

    def __bool__(self):
        return bool(len(self.input_queue))
