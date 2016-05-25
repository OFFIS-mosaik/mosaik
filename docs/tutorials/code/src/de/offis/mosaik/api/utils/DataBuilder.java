package de.offis.mosaik.api.utils;

import java.util.Map;

import org.json.simple.JSONObject;

/**
 * Used for building data mappings via 
 * {@link #addEntry(String, String, Object) addEntry()},
 * which can be used as return values of 
 * {@link de.offis.mosaik.api.Simulator#getData(Map) getData()}.
 * @author tLaue
 *
 */
public class DataBuilder {

	private JSONObject data = new JSONObject();
	private JSONObject cachedEntry;
	private String cachedEID;
	
	/**
	 * Instantiate a new 
	 * {@link de.offis.mosaik.api.utils.DataBuilder DataBuilder}.
	 */
	public DataBuilder() { }

	/**
	 * Append a new attribute-value pair to the entry of the specified
	 * entity ID. If there is no such entry a new one will be created.
	 * Will throw an exception if eid or attributeName are null.
	 * @param eid The ID of the entity whose attribute value is to be added.
	 * @param attributeName The name of the attribute.
	 * @param value The value of the attribute.
	 */
	@SuppressWarnings("unchecked")
	public void addEntry(String eid, String attributeName, 
			Object attributeValue) {
		if (eid == null || attributeName == null) {
			throw new RuntimeException("eid and attributeName can't be null");
		}
		JSONObject dataEntry;
		if (eid.equals(cachedEID)) {
			dataEntry = cachedEntry;
		} else {
			dataEntry = (JSONObject) data.get(eid);
			if (dataEntry == null) {
				dataEntry = new JSONObject();
				data.put(eid, dataEntry);
			}
			cachedEntry = dataEntry;
			cachedEID = eid;
		}
		dataEntry.put(attributeName, attributeValue);
	}

	/**
	 * Get all the data collected by this builder. <br>
	 * <em>Warning:</em> The returned mappings are no deep copies of the
	 * collected data, thus all changes to the output of this function will
	 * affect the collected data of this builder instance as well as all 
	 * its future outputs.
	 * @return The data as a mapping from entity IDs to a list of
	 * parameter-value-pairs.
	 */
	@SuppressWarnings("unchecked")
	public Map<String, Object> getOutput() {
		return this.data;
	}
}
