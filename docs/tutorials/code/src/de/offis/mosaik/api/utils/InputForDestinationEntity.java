package de.offis.mosaik.api.utils;

import java.util.Arrays;
import java.util.Iterator;
import java.util.Map;

/**
 * Contains an Array of 
 * {@link de.offis.mosaik.api.utils.AttributeInput AttributeInput} for a
 * specific destination entity, whose ID is stored in this object as well.
 * @author tLaue
 *
 */
public class InputForDestinationEntity implements Iterable<AttributeInput> {
	
	private String toEid;
	private AttributeInput[] inputs;
	
	@SuppressWarnings("unused")
	private InputForDestinationEntity() {}
	
	InputForDestinationEntity(String eid, Map<String, 
			Map<String, Object>> rawData) {
		this.toEid = eid;
		this.inputs = new AttributeInput[rawData.size()];
		int i = 0;
		for (Map.Entry<String, Map<String, Object>> e : rawData.entrySet()) {
			this.inputs[i] = new AttributeInput(e.getKey(), e.getValue());
			i++;
		}
	}
	
	/**
	 * Get the ID of the entity these inputs are intended for.
	 * @return The ID of the entity these inputs are intended for.
	 */
	public String getDestinatonEid() {
		return toEid;
	}
	
	/**
	 * Get the list of attribute inputs held by this object.
	 * @return The list of attribute inputs held by this object.
	 */
	public AttributeInput[] getAttributeInputs() {
		return inputs;
	}
	
	/**
	 * Among this entity input, find the list of inputs for the specified
	 * attribute.
	 * @param attributeName The attribute to find.
	 * @return The list of inputs for the attribute.
	 */
	public AttributeInput getAttributeInputByName(String attributeName) {
		for(AttributeInput inputs: this.inputs) {
			if (inputs.getAttributeName().equals(attributeName)) {
				return inputs;
			}
		}
		return null;
	}

	@Override
	public Iterator<AttributeInput> iterator() {
		return Arrays.asList(this.inputs).iterator();
	}
}
