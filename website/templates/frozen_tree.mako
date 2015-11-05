<%inherit file="base.mako"/>
<%def name="title()">Frozen Trees</%def>
<%def name="content()">

        % for user_id, user in user_dumps.items():
            <h1>${user_id}: ${diff[user_id]}</h1>
            <pre>
                ${user | h}
            </pre>
        % endfor


</%def>
