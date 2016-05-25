package de.offis.mosaik.api.utils;

/**
 * Represents a single key-value pair, where the key is an entities ID
 * and the value is the attribute value for a specific entity and attribute
 * originating from this entity.
 * @author tLaue
 *
 */
public class InputsFromSourceEntity {
	
	private String fromEid;
	private Object data;
	
	@SuppressWarnings("unused")
	private InputsFromSourceEntity() {};
	
	InputsFromSourceEntity(String eid, Object data) {
		this.fromEid = eid;
		this.data = data;
	};
	
	/**
	 * Get the ID of the source entity.
	 * @return The ID of the source entity.
	 */
	public String getSourceEid() {
		return fromEid;
	}

	/**
	 * Get the value.
	 * @return The value.
	 */
	public Object getValue() {
		return data;
	}
}
