package de.offis.mosaik.api.utils;

import java.util.Collection;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Contains information about the attribute values requested from 
 * certain entities by the mosaik framework in the 
 * {@link de.offis.mosaik.api.Simulator#getData(Map) getData()} API function.
 * Internally, this class is a facade to a {@code Map<String, List<String>>}
 * (which can be obtained for direct use via 
 * {@link #getRawData() getRawData()}).
 * The data is stored as follows:
 * <pre>{@code
{
	'eid_1': ['attr_1', 'attr_2', ...],
	...
}
	</pre>
 * @author tLaue
 *
 */
public class DataRequest {
	
	private Map<String, List<String>> request;
	
	public DataRequest(Map<String, List<String>> request) {
		this.request = request;
	}
	
	/**
	 * Returns true if the entity ID specified is contained in this request.
	 * @param eid The parameter name whose presence is to be tested.
	 * @return True, if entity ID could be found.
	 */
	public boolean containsKey(String eid) {
		return request.containsKey(eid);
	}

	/**
	 * Returns true if this request holds the specified attribute
	 * list at least once.
	 * @param attributeList Attribute list whose presence is to be tested.
	 * @return True if this request holds the specified attribute list at
	 * least once.
	 */
	public boolean containsValue(List<String> attributeList) {
		return request.containsValue(attributeList);
	}

	/**
	 * Returns a Set view of the entity ID-attributes pairs contained
	 * in this request.
	 * @return A set view of the mappings contained in this request.
	 */
	public Set<java.util.Map.Entry<String, List<String>>> entrySet() {
		return request.entrySet();
	}

	/**
	 * Returns the attribute list to which the specified entity ID name
	 * is mapped, or null, 
	 * if the entity ID is not present among the entity IDs in this request.
	 * @param eid The name of the entity ID whose associated attribute list
	 * you want to retrieve.
	 * @return The attribute list, or null.
	 */
	public List<String> get(String eid) {
		return request.get(eid);
	}
	
	/**
	 * Check whether this object holds no data.
	 * @return True, if this object holds no data.
	 */
	public boolean isEmpty() {
		return request.isEmpty();
	}

	/**
	 * Returns a Set view of the entity IDs contained in this request.
	 * @return A Set view of the entity IDs contained in this request
	 */
	public Set<String> keySet() {
		return request.keySet();
	}

	/**
	 * Returns the number of entity ID mappings in this request.
	 * @return The number of entity ID mappings in this request.
	 */
	public int size() {
		return request.size();
	}

	/**
	 * Returns a collection view of the attribute lists contained in
	 * this object.
	 * @return A collection view of the attribute lists contained in
	 * this object.
	 */
	public Collection<List<String>> values() {
		return request.values();
	}

	/**
	 * Get the raw data sent by mosaik.
	 * @return The data.
	 */
	public Map<String, List<String>> getRawData() {
		return this.request;
	}
}
