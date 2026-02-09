import ckan.plugins as p
import ckan.model as model
from ckan.common import request
from ckan.lib.base import h
import ckan.plugins.toolkit as toolkit

import logging
log = logging.getLogger(__name__)

def group_tree(organizations=[], type_='organization'):
    full_tree_list = p.toolkit.get_action('group_tree')({}, {'type': type_})
    if not organizations:
        return full_tree_list
    else:
        filtered_tree_list = group_tree_filter(organizations, full_tree_list)
        return filtered_tree_list


def group_tree_filter(organizations, group_tree_list, highlight=False):
    # this method leaves only the sections of the tree corresponding to the list
    # since it was developed for the users, all children organizations from the 
    # organizations in the list are included
    def traverse_select_highlighted(group_tree, selection=[], highlight=False):
        # add highlighted branches to the filtered tree
        if group_tree['highlighted']:
            # add to the selection and remove highlighting if necessary
            if highlight:
                selection += [group_tree]
            else:
                selection += group_tree_highlight([], [group_tree])
        else:
            # check if there is any highlighted child tree
            for child in group_tree.get('children', []):
                traverse_select_highlighted(child, selection)

    filtered_tree=[]
    # first highlights all the organizations from the list in the three
    for group in group_tree_highlight(organizations, group_tree_list):
        traverse_select_highlighted(group, filtered_tree, highlight)

    return filtered_tree


def group_tree_section(id_, type_='organization', include_parents=True, include_siblings=True):
    return p.toolkit.get_action('group_tree_section')(
        {'include_parents':include_parents, 'include_siblings':include_siblings}, {'id': id_, 'type': type_,})

def group_tree_parents(id_, type_='organization'):
     tree_node =  p.toolkit.get_action('organization_show')({},{'id':id_})
     if (tree_node['groups']):
         parent_id = tree_node['groups'][0]['name']
         parent_node =  p.toolkit.get_action('organization_show')({},{'id':parent_id})
         return group_tree_parents(parent_id) + [parent_node]
     else:
         return []

def group_tree_get_longname(id_, default="", type_='organization'):
     tree_node =  p.toolkit.get_action('organization_show')({},{'id':id_})
     longname = tree_node.get("longname", default)
     if not longname:
         return default
     return longname

def group_tree_highlight(organizations, group_tree_list):

    def traverse_highlight(group_tree, name_list):
        if group_tree.get('name', "") in name_list:
            group_tree['highlighted'] = True
        else:
            group_tree['highlighted'] = False
        for child in group_tree.get('children', []):
            traverse_highlight(child, name_list)

    selected_names = [ o.get('name',None) for o in organizations]

    for group in group_tree_list:
        traverse_highlight(group, selected_names)
    return group_tree_list

def get_allowable_parent_groups(user, group_id):
    allowable_parent_groups = toolkit.get_action(u'organization_list_for_user')(
            {u'user': user}, {u'permission': u'admin'})
    # exclude groups that could create a loop
    if group_id:
        group = model.Group.get(group_id)
        allowable_unloopable_groups = group.groups_allowed_to_be_its_parent(type='organization')
        allowable_group_names = [group.name for group in allowable_unloopable_groups]
        return [group for group in allowable_parent_groups
                if group.get('name') in allowable_group_names]

    return allowable_parent_groups

def is_include_children_selected(fields):
    include_children_selected = False
    if request.params.get('include_children'):
        include_children_selected = True
    return include_children_selected


def group_depth(group_id):
    depth = 0
    group = group_tree_section(group_id, include_siblings=False)
    if group['highlighted'] == True:
        return depth
    else:    
        while group['children']:
            if group['highlighted'] == True:
                return depth
            else:
                depth += 1
                group = group['children'][0]
    return depth            


def available_orgs_names():
    available_orgs = h.organizations_available('create_dataset')
    org_names = []
    for org in available_orgs:
        org_names.append(org['name'])
    
    return org_names


# def render_tree():
#     '''Returns HTML for a hierarchy of all publishers'''
#     from ckan.logic import get_action
#     from ckan import model
#     context = {'model': model, 'session': model.Session}
#     top_nodes = get_action('group_tree')(context=context,
#             data_dict={'type': 'organization'})
#     return _render_tree(top_nodes)

def render_tree(top_nodes):
    html = '<ul class="org-tree">'
    for node in top_nodes:
        html += _render_collapsible_node(node)
    html += '</ul>'
    return html

def _render_tree(top_nodes):
    html = '<ul class="org-tree">'
    for node in top_nodes:
        html += _render_collapsible_node(node)
    html += '</ul>'
    return html

def _render_collapsible_node(node):
    has_children = node.get("children") and len(node["children"]) > 0
    toggle_btn = f'<button class="toggle-btn" data-org="{node["name"]}">+</button>' if has_children else ""

    html = f'''
    <li class="dataset-item" id="node_{node['name']}" style="list-style: none;">
      <div class="row dataset-content">
        <div class="col-12 col-md-6">
          <div class="d-flex align-items-center gap-2 node">
            
            <h3 class="organization-heading m-0">
              <a href="/organization/{node['name']}">{node['title']}</a>
            </h3>
          </div>
          <ul class="children ps-4" id="children_{node['name']}" style="display:none;"></ul>
        </div>
      </div>
    </li>
    '''
    return html


def _render_tree_node(node):
    html = '<a href="/organization/%s">%s</a>' % (node['name'], node['title'])
    if node.get('highlighted'):
        html = '<strong>%s</strong>' % html
    if node.get("children"):
        html += '<ul>'
        for child in node['children']:
            html += _render_tree_node(child)
        html += '</ul>'
    html = '<li id="node_%s">%s</li>' % (node['name'], html)
    return html
