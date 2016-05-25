package de.offis.mosaik.api.utils;

import java.util.HashMap;
import java.util.LinkedList;
import java.util.List;
import java.util.Map;

import org.json.simple.JSONArray;

/**
 * A utility class to simplify creation of entity maps you need to return from
 * your 
 * {@link de.offis.mosaik.api.Simulator#create(int, String, Map) create()}
 * implementation. It provides automatic entity ID management (see 
 * {@link #addEntityDescription(String, String[]) addEntityDescription()}).
 * @author tLaue
 *
 */
@SuppressWarnings("unchecked")
public class EntityDescriptionBuilder {
	
	private static HashMap<String, HashMap<String, Integer>> globalCounts 
		= new HashMap<>();

	private LinkedList <EntityDescription> entities = new LinkedList<>();
	private String eidPrefix;
	
	/**
	 * Create a new EntityDescriptionBuilder instance.
	 */
	public EntityDescriptionBuilder() {
		this.eidPrefix = "";
		if (!globalCounts.containsKey(this.eidPrefix)) {
			globalCounts.put(eidPrefix, new HashMap<>());
		}
	}
	
	/**
	 * Create a new EntityDescriptionBuilder instance with the specified
	 * String as entity ID prefix, which will be used for automatic entity
	 * ID generation.
	 * @param eidPrefix The entity ID prefix.
	 */
	public EntityDescriptionBuilder(String eidPrefix) {
		this.eidPrefix = eidPrefix + "_";
		if (!globalCounts.containsKey(this.eidPrefix)) {
			globalCounts.put(this.eidPrefix, new HashMap<>());
		}
	}

	/**
	 * Add a new
	 * {@link de.offis.mosaik.api.utils.EntityDescription EntityDescription}.
	 * Will throw an exception if the entity already exists, or if eid or 
	 * type are null.
	 * @param eid The unique ID of the entity.
	 * @param type The model type of this entity.
	 * @param rel A list of the IDs of related entities (optional).
	 * @return The newly added entity as a 
	 * {@link de.offis.mosaik.api.utils.EntityDescription EntityDescription} 
	 * instance (can be used for appending children entities to it).
	 */
	public EntityDescription addEntityDescription(String eid, String type, 
			String[] rel) {
		if (type == null || eid == null) {
			throw new RuntimeException("eid and type can not be null.");
		}
		HashMap<String, Integer> modelCounts = globalCounts
				.get(this.eidPrefix);
		Integer count = modelCounts.get(type);
		if (count == null) {
			count = new Integer(0);
			modelCounts.put(type, count);
		}
		int countInt = count.intValue();
		
		countInt++;
		modelCounts.put(type, new Integer(countInt));
		
		EntityDescription ent2 = this.getEntityDescriptionByEid(eid);
		
		if (ent2 != null) {
			throw new RuntimeException("Eid " + eid + " is not unique! Type: "
					+ ent2.getType()+ ", EID: "+ ent2.getEID());
		}
		
		EntityDescription entity = new EntityDescription(eid, type, rel);
		this.entities.add(entity);
		return entity;
	}

	/**
	 * Add a new 
	 * {@link de.offis.mosaik.api.utils.EntityDescription EntityDescription}.
	 * This function will automatically generate an ID for the child,
	 * following the scheme<br>
	 * {@code [eid prefix_]+[entity type]}
	 * {@code +_+[0 based index of entities of the same type]}<br>
	 * Will throw an exception if the EID already exists, or if type is null.
	 * @param type The model type of this entity.
	 * @param rel A list of the IDs of related entities (optional).
	 * @return The newly created entity as a 
	 * {@link de.offis.mosaik.api.utils.EntityDescription EntityDescription}
	 * instance (can be used for appending children entities to it, of for 
	 * retrieving its automatically generated ID).
	 */
	public EntityDescription addEntityDescription(String type, String[] rel) {
		if (type == null) {
			throw new RuntimeException("type can not be null.");
		}
		
		HashMap<String, Integer> modelCounts = globalCounts
				.get(this.eidPrefix);
		Integer count = modelCounts.get(type);
		if (count == null) {
			count = new Integer(0);
			modelCounts.put(type, count);
		}
		int countInt = count.intValue();

		String autoEid = this.eidPrefix + type + "_" + countInt;
		
		countInt++;
		modelCounts.put(type, new Integer(countInt));
		
		EntityDescription ent2 = this.getEntityDescriptionByEid(autoEid);
		
		if (ent2 != null) {
			throw new RuntimeException("Eid " + autoEid + " is not unique! "
					+ "Type: " + ent2.getType()+ ", EID: "+ ent2.getEID());
		}
		
		EntityDescription entity = new EntityDescription(autoEid, type, rel);
		this.entities.add(entity);
		return entity;
	}
	

	/**
	 * Get all entity entries contained in this object.
	 * @return  A JSON array of entities (in a form that can be returned 
	 * directly in your 
	 * {@link de.offis.mosaik.api.Simulator#create(int, String, Map) create()}
	 * implementation).<br>
	 */
	public List<Map<String, Object>> getOutput() {
		JSONArray jArray = new JSONArray();
        for (EntityDescription e : this.entities) {
            jArray.add(e.toJSONObject());
        }
		return jArray;
	}
	
	/**
	 * Get this factory's entity ID prefix.
	 * @return The prefix, or null.
	 */
	public String getEidPrefix() {
		return this.eidPrefix;
	}
	
	/**
	 * Finds an entity by ID (search will include children entries).
	 * @param eid The ID in question.
	 * @return The entity with the specified ID, or null.
	 */
	private EntityDescription getEntityDescriptionByEid(String eid) {
		EntityDescription result = null;
		for (EntityDescription ent : this.entities) {
			if (ent.getEID().equals(eid)) {
				result = ent;
				break;
			} else if (ent.getChildren() != null) {
				result = ent.getChildByEid(eid);
			}
			if (result != null) {
				break;
			}
		}
		return result;
	}
}