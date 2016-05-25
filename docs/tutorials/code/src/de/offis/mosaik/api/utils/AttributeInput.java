package de.offis.mosaik.api.utils;

import java.util.Arrays;
import java.util.Iterator;
import java.util.Map;

/**
 * Represents all inputs for a specific destination entity under 
 * a specific attribute, which are stored as an array of
 * {@link de.offis.mosaik.api.utils.InputsFromSourceEntity 
 * InputsFromSourceEntity}.
 * @author tLaue
 *
 */
public class AttributeInput implements Iterable<InputsFromSourceEntity>{

	private String attributeName;
	private InputsFromSourceEntity[] inputs;
	
	@SuppressWarnings("unused")
	private AttributeInput() {}
	
	AttributeInput(String attributeName , Map<String, Object> rawData) {
		this.attributeName = attributeName;
		this.inputs = new InputsFromSourceEntity[rawData.size()];
		int i = 0;
		for (Map.Entry<String,  Object> entry : rawData.entrySet()) {
			this.inputs[i] = new InputsFromSourceEntity(entry.getKey(),
					entry.getValue());
			i++;
		}
	}
	
	/**
	 * Get the name of the attribute whose inputs are held by this object.
	 * @return The name of the attribute whose inputs are held by this object.
	 */
	public String getAttributeName() {
		return attributeName;
	}

	/**
	 * Get the inputs from all sources for this attribute.
	 * @return The inputs from all sources for this attribute.
	 */
	public InputsFromSourceEntity[] getSourceInputs() {
		return inputs;
	}

	/**
	 * Get the input for this attribute by a specific source.
	 * @param eid The source entities ID.
	 * @return The input.
	 */
	public InputsFromSourceEntity getInputByEid(String eid) {
		for (InputsFromSourceEntity inputs : this.inputs) {
			if (inputs.getSourceEid().equals(eid)) {
				return inputs;
			}
		}
		return null;
	}

	@Override
	public Iterator<InputsFromSourceEntity> iterator() {
		return Arrays.asList(this.inputs).iterator();
	}
}
