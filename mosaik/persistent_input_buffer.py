import heapq as hq


class PersistentInputBuffer:
    def __init__(self):
        self.input_queue = []
        self.memory = {}

    def set_connections(self, src_sid, src_eid, dest_eid, attr_pairs,
                        initial_data):
        src_full_id = '.'.join(map(str, (src_sid, src_eid)))

        for src_var, dest_var in attr_pairs:
            self.memory.setdefault(dest_eid, {}).setdefault(dest_var, {})[
                src_full_id] = initial_data.get(dest_eid, {}).get(dest_var, None)

    def add(self, time, src_sid, src_eid, dest_eid, dest_var, value):
        src_full_id = '.'.join(map(str, (src_sid, src_eid)))
        hq.heappush(self.input_queue, (time, src_full_id, dest_eid, dest_var, value))

    def get_input(self, step):
        input = self.memory
        while len(self.input_queue) > 0 and self.input_queue[0][0] <= step:
            _, src_full_id, eid, attr, value = hq.heappop(self.input_queue)
            input[eid][attr][src_full_id] = value
        print('TB input', input)

        return input

    def __bool__(self):
        return bool(len(self.input_queue))
