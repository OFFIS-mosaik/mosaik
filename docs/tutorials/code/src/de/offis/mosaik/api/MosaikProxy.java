package de.offis.mosaik.api;

import java.util.Arrays;
import java.util.List;
import java.util.Map;

import org.json.simple.JSONArray;

/**
 * This class is a proxy to mosaik that allows you to query it for simulation
 * or simulator data.
 */
public class MosaikProxy {
    private final SimpyIoSocket sock;

    /**
     * Create a proxy object for a simpy.io socket.
     *
     * @param sock is the simpy.io socket connected to mosaik.
     */
    public MosaikProxy(SimpyIoSocket sock) {
        this.sock = sock;
    }

    /**
     * Get the current simulation progress.
     *
     * @return the simulation progress in per-cent.
     * @throws Exception
     */
    public float getProgress() throws Exception {
        return ((Number) this.sock.makeRequest("get_progress")).floatValue();
    }

    /**
     * Get the complete entity graph, e.g.:
     *
     * <pre>{
     *     'nodes': {
     *         'sid_0.eid_0': {'type': 'A'},
     *         'sid_0.eid_1': {'type': 'B'},
     *         'sid_1.eid_0': {'type': 'C'},
     *     },
     *     'edges': [
     *         ['sid_0.eid_0', 'sid_1.eid0', {}],
     *         ['sid_0.eid_1', 'sid_1.eid0', {}],
     *     ],
     * }</pre>
     *
     * @return the complete entity graph.
     * @throws Exception
     */
    @SuppressWarnings("unchecked")
    public Map<String, Object> getRelatedEntities() throws Exception {
        return (Map<String, Object>) this.sock
                .makeRequest("get_related_entities");
    }

    /**
     * Get all entities related to another entity <em>fullId</em>, e.g.:
     *
     * <pre>{
     *     'sid_0.eid_0': {'type': 'A'},
     *     'sid_0.eid_1': {'type': 'B'},
     * }</pre>
     *
     * @param fullId is the full entity ID for which to query related entities.
     * @return a map of related entity IDs.
     * @throws Exception
     */
    @SuppressWarnings("unchecked")
    public Map<String, Object> getRelatedEntities(String fullId)
            throws Exception {
        final JSONArray args = new JSONArray();
        args.add(fullId);
        return (Map<String, Object>) this.sock.makeRequest(
                "get_related_entities", args);
    }

    /**
     * Get all entities related to a list of other entities, e.g.:
     *
     * <pre>{
     *     'sid_0.eid_0': {
     *         'sid_0.eid_1': {'type': 'B'},
     *     },
     *     'sid_0.eid_1': {
     *         'sid_0.eid_1': {'type': 'B'},
     *     },
     * }</pre>
     *
     * @param fullIds is a list of full entity IDs.
     * @return a map of related entitis.
     * @throws Exception
     */
    @SuppressWarnings("unchecked")
    public Map<String, Object> getRelatedEntities(String[] fullIds)
            throws Exception {
        final JSONArray args = new JSONArray();
        args.add(Arrays.asList(fullIds));
        return (Map<String, Object>) this.sock.makeRequest(
                "get_related_entities", args);
    }

    /**
     * Return the data for the requested attributes <em>attrs</em>.
     *
     * *attrs* is a dict of (fully qualified) entity IDs mapping to lists of
     * attribute names (``{'sid/eid': ['attr1', 'attr2']}``).
     *
     * The return value is a dict mapping the input entity IDs to data
     * dictionaries mapping attribute names to there respective values
     * (``{'sid/eid': {'attr1': val1, 'attr2': val2}}``).

     * @param attrs is a map of (fully qualified) entity IDs mapping to lists
     *              of attribute names:
     *              <code>{'sid/eid': ['attr1', 'attr2']}</code>.
     * @return a map that maps the input entity IDs to data maps that with
     *         attributes and values:
     *         <code>{'sid/eid': {'attr1': val1, 'attr2': val2}}</code>.
     * @throws Exception
     */
    @SuppressWarnings("unchecked")
    public Map<String, Object> getData(Map<String, List<String>> attrs)
            throws Exception {
        final JSONArray args = new JSONArray();
        args.add(attrs);
        return (Map<String, Object>) this.sock.makeRequest("get_data", args);
    }

    /**
     * Set <em>data</em> as input data for all affected simulators.
     *
     * @param data is a map mapping source entity IDs to destination entity IDs
     *             with maps of attributes and values:
     *             <code>{'src_full_id': {'dest_full_id':
     *             {'attr1': 'val1', 'attr2': 'val2'}}}</code>
     * @throws Exception
     */
    @SuppressWarnings("unchecked")
    public void setData(Map<String, Object> data) throws Exception {
        final JSONArray args = new JSONArray();
        args.add(data);
        this.sock.makeRequest("set_data", args);
    }
}
