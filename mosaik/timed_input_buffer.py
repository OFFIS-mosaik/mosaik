import heapq as hq


class InputBuffer:
    def __init__(self):
        self.input_map = {}
        self.input_queue = []

    def set_connection(self, src_sid, src_eid, src_var, dest_eid, dest_var):
        src_full_id = '.'.join(map(str, (src_sid, src_eid)))
        self.input_map.setdefault((src_full_id, src_var), set()).add((dest_eid, dest_var))

    def add(self, time, src_sid, src_eid, src_var, value):
        src_full_id = '.'.join(map(str, (src_sid, src_eid)))
        hq.heappush(self.input_queue, (time, src_full_id, src_var, value))

    def get_input(self, step):
        input = {}
        while len(self.input_queue) > 0 and self.input_queue[0][0] <= step:
            _, src_full_id, src_var, value = hq.heappop(self.input_queue)

            for eid, attr in self.input_map[(src_full_id, src_var)]:
                input.setdefault(eid, {}).setdefault(attr, {})[src_full_id] = value
        print('TB input', input)

        return input

    def __bool__(self):
        return bool(len(self.input_queue))
